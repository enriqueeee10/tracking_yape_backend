from sqlalchemy.orm import Session
from app.models import (
    DBDeviceUser,
    DBGroupSchedule,
    DBIndividualSchedule,
    DBUser,
    UserRole,
)
from app.schemas import (
    GroupScheduleCreate,
    GroupScheduleOut,
    IndividualScheduleCreate,
    IndividualScheduleOut,
    ScheduleUpdate,
)
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.working_group_repository import WorkingGroupRepository
from app.repositories.device_repository import DeviceRepository
from app.repositories.user_repository import UserRepository
from fastapi import HTTPException, status
from typing import Optional, List
from datetime import datetime


class ScheduleService:
    def __init__(self, db: Session):
        self.schedule_repo = ScheduleRepository(db)
        self.group_repo = WorkingGroupRepository(db)
        self.device_repo = DeviceRepository(db)
        self.user_repo = UserRepository(db)
        self.db = db

    # --- Group Schedules ---
    def create_group_schedule(
        self, schedule_data: GroupScheduleCreate, group_id: int, current_user: DBUser
    ) -> GroupScheduleOut:
        # Solo el admin del grupo puede crear o actualizar horarios de grupo
        group = self.group_repo.get_working_group_by_id(group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Grupo de trabajo no encontrado.",
            )
        if current_user.role != UserRole.ADMIN or group.creator_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para gestionar horarios de este grupo.",
            )

        new_schedule = DBGroupSchedule(
            working_group_id=group_id,
            start_time=schedule_data.start_time,
            end_time=schedule_data.end_time,
            all_day=schedule_data.all_day,
            is_active=schedule_data.is_active,
        )
        created_schedule = self.schedule_repo.create_group_schedule(new_schedule)
        return GroupScheduleOut.model_validate(created_schedule)

    def get_group_schedules(
        self, group_id: int, current_user: DBUser
    ) -> List[GroupScheduleOut]:
        group = self.group_repo.get_working_group_by_id(group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Grupo de trabajo no encontrado.",
            )

        # Verificar permisos para ver los horarios del grupo
        is_admin_of_group = (
            current_user.role == UserRole.ADMIN and group.creator_id == current_user.id
        )
        is_member_of_group = any(
            du.device.working_group_id == group_id for du in current_user.user_devices
        )
        if not (is_admin_of_group or is_member_of_group):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para ver los horarios de este grupo.",
            )

        schedules = self.schedule_repo.get_group_schedules_by_group(group_id)
        return [GroupScheduleOut.model_validate(schedule) for schedule in schedules]

    def update_group_schedule(
        self, schedule_id: int, schedule_data: ScheduleUpdate, current_user: DBUser
    ) -> GroupScheduleOut:
        schedule_to_update = self.schedule_repo.get_group_schedule_by_id(schedule_id)
        if not schedule_to_update:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Horario de grupo no encontrado.",
            )

        # Solo el admin del grupo puede actualizar
        group = self.group_repo.get_working_group_by_id(
            schedule_to_update.working_group_id
        )
        if (
            not group
            or current_user.role != UserRole.ADMIN
            or group.creator_id != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para actualizar este horario.",
            )

        update_data = schedule_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(schedule_to_update, key, value)

        updated_schedule = self.schedule_repo.update_group_schedule(schedule_to_update)
        return GroupScheduleOut.model_validate(updated_schedule)

    def delete_group_schedule(self, schedule_id: int, current_user: DBUser):
        schedule = self.schedule_repo.get_group_schedule_by_id(schedule_id)
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Horario de grupo no encontrado.",
            )

        group = self.group_repo.get_working_group_by_id(schedule.working_group_id)
        if (
            not group
            or current_user.role != UserRole.ADMIN
            or group.creator_id != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para eliminar este horario.",
            )

        self.schedule_repo.delete_group_schedule(schedule)

    # --- Individual Schedules ---
    def create_individual_schedule(
        self, schedule_data: IndividualScheduleCreate, current_user: DBUser
    ) -> IndividualScheduleOut:
        # Validar que al menos uno de device_user_id, device_id, user_id esté presente
        if not (
            schedule_data.device_user_id
            or schedule_data.device_id
            or schedule_data.user_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Se debe especificar device_user_id, device_id o user_id para un horario individual.",
            )

        # Verificar permisos (solo admin del grupo o el propio usuario/dispositivo si tiene permiso)
        # Para simplificar: solo admins pueden crear horarios individuales al inicio.
        if current_user.role != UserRole.ADMIN and not (
            schedule_data.user_id == current_user.id
            and schedule_data.device_user_id is None
            and schedule_data.device_id is None
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para crear este horario individual.",
            )

        # Validar existencia de las FKs y que pertenezcan al grupo del admin
        if schedule_data.device_user_id:
            du = (
                self.db.query(DBDeviceUser)
                .filter(DBDeviceUser.id == schedule_data.device_user_id)
                .first()
            )
            if not du:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="DeviceUser no encontrado.",
                )
            if current_user.role == UserRole.ADMIN and (
                du.device.working_group_id
                not in [g.id for g in current_user.created_working_groups]
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No puedes crear horarios para DeviceUsers fuera de tu grupo.",
                )
        elif schedule_data.device_id:
            device = self.device_repo.get_device_by_id(schedule_data.device_id)
            if not device:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dispositivo no encontrado.",
                )
            if current_user.role == UserRole.ADMIN and (
                device.working_group_id
                not in [g.id for g in current_user.created_working_groups]
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No puedes crear horarios para dispositivos fuera de tu grupo.",
                )
        elif schedule_data.user_id:
            target_user = self.user_repo.get_user_by_id(schedule_data.user_id)
            if not target_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuario no encontrado.",
                )
            # Si el admin crea un horario para un usuario, el usuario debe pertenecer a su grupo
            if current_user.role == UserRole.ADMIN:
                if not (
                    target_user.id == current_user.id
                    or any(
                        du.device.working_group_id
                        in [g.id for g in current_user.created_working_groups]
                        for du in target_user.user_devices
                    )
                ):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="No puedes crear horarios para usuarios fuera de tu grupo.",
                    )

        new_schedule = DBIndividualSchedule(
            device_user_id=schedule_data.device_user_id,
            device_id=schedule_data.device_id,
            user_id=schedule_data.user_id,
            start_time=schedule_data.start_time,
            end_time=schedule_data.end_time,
            all_day=schedule_data.all_day,
            is_active=schedule_data.is_active,
        )
        created_schedule = self.schedule_repo.create_individual_schedule(new_schedule)
        return IndividualScheduleOut.model_validate(created_schedule)

    def get_individual_schedule_by_id(
        self, schedule_id: int, current_user: DBUser
    ) -> Optional[IndividualScheduleOut]:
        schedule = self.schedule_repo.get_individual_schedule_by_id(schedule_id)
        if not schedule:
            return None

        # Verificar permisos para ver el horario individual
        is_admin = current_user.role == UserRole.ADMIN
        belongs_to_user = schedule.user_id == current_user.id
        belongs_to_device_user = schedule.device_user_id and any(
            du.id == schedule.device_user_id for du in current_user.user_devices
        )
        belongs_to_device_group = schedule.device_id and any(
            d.id == schedule.device_id and d.working_group.creator_id == current_user.id
            for d in current_user.created_working_groups
        )  # Si el admin es creador del grupo del dispositivo

        if not (
            is_admin
            or belongs_to_user
            or belongs_to_device_user
            or belongs_to_device_group
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para ver este horario.",
            )

        return IndividualScheduleOut.model_validate(schedule)

    def update_individual_schedule(
        self, schedule_id: int, schedule_data: ScheduleUpdate, current_user: DBUser
    ) -> IndividualScheduleOut:
        schedule_to_update = self.schedule_repo.get_individual_schedule_by_id(
            schedule_id
        )
        if not schedule_to_update:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Horario individual no encontrado.",
            )

        # Verificar permisos para actualizar (solo admin o el propio usuario/dispositivo)
        is_admin = current_user.role == UserRole.ADMIN
        is_owner = schedule_to_update.user_id == current_user.id

        # Lógica más compleja si se trata de device_user_id o device_id
        if schedule_to_update.device_user_id:
            du = (
                self.db.query(DBDeviceUser)
                .filter(DBDeviceUser.id == schedule_to_update.device_user_id)
                .first()
            )
            if du and du.user_id == current_user.id:
                is_owner = True
            elif (
                is_admin
                and du
                and du.device.working_group_id
                in [g.id for g in current_user.created_working_groups]
            ):
                pass  # Admin puede actualizar si el device_user está en su grupo
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para actualizar este horario individual.",
                )
        elif schedule_to_update.device_id:
            device = self.device_repo.get_device_by_id(schedule_to_update.device_id)
            if (
                is_admin
                and device
                and device.working_group_id
                in [g.id for g in current_user.created_working_groups]
            ):
                pass  # Admin puede actualizar si el dispositivo está en su grupo
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para actualizar este horario individual.",
                )
        elif schedule_to_update.user_id:
            if not (is_admin or is_owner):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para actualizar este horario individual.",
                )

        update_data = schedule_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(schedule_to_update, key, value)

        updated_schedule = self.schedule_repo.update_individual_schedule(
            schedule_to_update
        )
        return IndividualScheduleOut.model_validate(updated_schedule)

    def delete_individual_schedule(self, schedule_id: int, current_user: DBUser):
        schedule = self.schedule_repo.get_individual_schedule_by_id(schedule_id)
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Horario individual no encontrado.",
            )

        is_admin = current_user.role == UserRole.ADMIN
        is_owner = schedule.user_id == current_user.id

        # Lógica más compleja si se trata de device_user_id o device_id
        if schedule.device_user_id:
            du = (
                self.db.query(DBDeviceUser)
                .filter(DBDeviceUser.id == schedule.device_user_id)
                .first()
            )
            if du and du.user_id == current_user.id:
                is_owner = True
            elif (
                is_admin
                and du
                and du.device.working_group_id
                in [g.id for g in current_user.created_working_groups]
            ):
                pass  # Admin puede eliminar si el device_user está en su grupo
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para eliminar este horario individual.",
                )
        elif schedule.device_id:
            device = self.device_repo.get_device_by_id(schedule.device_id)
            if (
                is_admin
                and device
                and device.working_group_id
                in [g.id for g in current_user.created_working_groups]
            ):
                pass  # Admin puede eliminar si el dispositivo está en su grupo
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para eliminar este horario individual.",
                )
        elif schedule.user_id:
            if not (is_admin or is_owner):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para eliminar este horario individual.",
                )

        self.schedule_repo.delete_individual_schedule(schedule)
