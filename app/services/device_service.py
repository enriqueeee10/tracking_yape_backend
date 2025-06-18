from sqlalchemy.orm import Session
from app.models import DBDevice, DBDeviceUser, DBUser
from app.schemas import (
    DeviceCreate,
    DeviceOut,
    DeviceUpdate,
    DeviceUserCreate,
    DeviceUserOut,
    UserOut,
)
from app.repositories.device_repository import DeviceRepository
from app.repositories.user_repository import UserRepository
from app.repositories.working_group_repository import WorkingGroupRepository
from fastapi import HTTPException, status
from typing import Optional, List
from datetime import datetime


class DeviceService:
    def __init__(self, db: Session):
        self.device_repo = DeviceRepository(db)
        self.user_repo = UserRepository(db)
        self.group_repo = WorkingGroupRepository(db)
        self.db = db

    def create_device(
        self, device_data: DeviceCreate, current_user: DBUser
    ) -> DeviceOut:
        # Solo el admin del grupo puede crear dispositivos para SU grupo
        # Asumimos que el admin tiene al menos un grupo creado
        if (
            current_user.role != DBUser.role.ADMIN
            or not current_user.created_working_groups
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores de un grupo pueden crear dispositivos.",
            )

        admin_group_id = current_user.created_working_groups[
            0
        ].id  # Asumimos el primer grupo del admin

        if device_data.working_group_id != admin_group_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puedes crear dispositivos para tu propio grupo.",
            )

        existing_device = self.device_repo.get_device_by_uid(device_data.device_uid)
        if existing_device:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un dispositivo con este UID.",
            )

        # Verificar que el grupo exista
        working_group = self.group_repo.get_working_group_by_id(
            device_data.working_group_id
        )
        if not working_group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Grupo de trabajo no encontrado.",
            )

        new_device = DBDevice(
            working_group_id=device_data.working_group_id,
            device_uid=device_data.device_uid,
            alias=device_data.alias,
            description=device_data.description,
            is_active=device_data.is_active,
            last_seen=datetime.utcnow(),  # Establecer last_seen al crear
        )
        created_device = self.device_repo.create_device(new_device)
        return DeviceOut.model_validate(created_device)

    def get_device_by_id(
        self, device_id: int, current_user: DBUser
    ) -> Optional[DeviceOut]:
        device = self.device_repo.get_device_by_id(device_id)
        if not device:
            return None

        # Solo usuarios del mismo grupo pueden ver el dispositivo
        user_group_id = (
            current_user.created_working_groups[0].id
            if current_user.created_working_groups
            else (
                current_user.user_devices[0].device.working_group_id
                if current_user.user_devices
                else None
            )
        )
        if user_group_id != device.working_group_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para ver este dispositivo.",
            )

        return DeviceOut.model_validate(device)

    def get_devices_for_group(
        self, group_id: int, current_user: DBUser
    ) -> List[DeviceOut]:
        # Verificar que el usuario pertenezca o sea admin del grupo
        is_admin_of_group = current_user.role == DBUser.role.ADMIN and any(
            g.id == group_id for g in current_user.created_working_groups
        )
        is_member_of_group = any(
            du.device.working_group_id == group_id for du in current_user.user_devices
        )

        if not (is_admin_of_group or is_member_of_group):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para ver los dispositivos de este grupo.",
            )

        devices = self.device_repo.get_devices_by_group(group_id)
        return [DeviceOut.model_validate(device) for device in devices]

    def update_device(
        self, device_id: int, device_data: DeviceUpdate, current_user: DBUser
    ) -> DeviceOut:
        device_to_update = self.device_repo.get_device_by_id(device_id)
        if not device_to_update:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispositivo no encontrado.",
            )

        # Solo el admin del grupo al que pertenece el dispositivo puede actualizarlo
        admin_group_id = (
            current_user.created_working_groups[0].id
            if current_user.created_working_groups
            else None
        )
        if (
            current_user.role != DBUser.role.ADMIN
            or device_to_update.working_group_id != admin_group_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para actualizar este dispositivo.",
            )

        update_data = device_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(device_to_update, key, value)

        updated_device = self.device_repo.update_device(device_to_update)
        return DeviceOut.model_validate(updated_device)

    def deactivate_device(self, device_id: int, current_user: DBUser) -> DeviceOut:
        device = self.device_repo.get_device_by_id(device_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispositivo no encontrado.",
            )

        admin_group_id = (
            current_user.created_working_groups[0].id
            if current_user.created_working_groups
            else None
        )
        if (
            current_user.role != DBUser.role.ADMIN
            or device.working_group_id != admin_group_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para desactivar este dispositivo.",
            )

        device.is_active = False
        deactivated_device = self.device_repo.update_device(device)
        return DeviceOut.model_validate(deactivated_device)

    def assign_user_to_device(
        self, device_user_data: DeviceUserCreate, current_user: DBUser
    ) -> DeviceUserOut:
        # Verificar que el usuario que asigna sea el admin del grupo del dispositivo
        device = self.device_repo.get_device_by_id(device_user_data.device_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispositivo no encontrado.",
            )

        admin_group_id = (
            current_user.created_working_groups[0].id
            if current_user.created_working_groups
            else None
        )
        if (
            current_user.role != DBUser.role.ADMIN
            or device.working_group_id != admin_group_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para asignar usuarios a este dispositivo.",
            )

        # Verificar que el usuario exista y pertenezca al mismo grupo (o sea el admin)
        target_user = self.user_repo.get_user_by_id(device_user_data.user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario a asignar no encontrado.",
            )

        # Si el target_user es un miembro, debe estar asociado al mismo grupo del dispositivo
        # O ser el propio admin asignándose a un dispositivo de su grupo.
        # Simplificación: Asumimos que los miembros se crean y luego se asocian.
        # Aquí, si el target_user no es ADMIN, debe estar en el grupo del device.
        # Esto es complejo porque la pertenencia de un miembro al grupo es a través de device_users.
        # Para simplificar: solo permite que el admin asigne a CUALQUIER usuario,
        # pero la implicación es que ese usuario "pertenece" al grupo al ser asociado a un dispositivo del grupo.

        existing_association = self.device_repo.get_device_user_association(
            device_user_data.user_id, device_user_data.device_id
        )
        if existing_association:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario ya está asignado a este dispositivo.",
            )

        new_association = DBDeviceUser(
            user_id=device_user_data.user_id,
            device_id=device_user_data.device_id,
            is_active=device_user_data.is_active,
        )
        created_association = self.device_repo.create_device_user_association(
            new_association
        )
        return DeviceUserOut.model_validate(created_association)

    def get_users_assigned_to_device(
        self, device_id: int, current_user: DBUser
    ) -> List[UserOut]:
        device = self.device_repo.get_device_by_id(device_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispositivo no encontrado.",
            )

        # Solo usuarios del mismo grupo pueden ver las asignaciones
        user_group_id = (
            current_user.created_working_groups[0].id
            if current_user.created_working_groups
            else (
                current_user.user_devices[0].device.working_group_id
                if current_user.user_devices
                else None
            )
        )
        if user_group_id != device.working_group_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para ver las asignaciones de este dispositivo.",
            )

        associations = self.device_repo.get_device_users_by_device(device_id)
        users = [
            self.user_repo.get_user_by_id(assoc.user_id)
            for assoc in associations
            if self.user_repo.get_user_by_id(assoc.user_id) is not None
        ]
        return [UserOut.model_validate(user) for user in users]

    def remove_user_from_device(self, device_user_id: int, current_user: DBUser):
        association = (
            self.db.query(DBDeviceUser)
            .filter(DBDeviceUser.id == device_user_id)
            .first()
        )
        if not association:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asociación dispositivo-usuario no encontrada.",
            )

        # Verificar permisos: solo el admin del grupo del dispositivo puede remover
        device = self.device_repo.get_device_by_id(association.device_id)
        admin_group_id = (
            current_user.created_working_groups[0].id
            if current_user.created_working_groups
            else None
        )
        if (
            current_user.role != DBUser.role.ADMIN
            or device.working_group_id != admin_group_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para remover esta asignación.",
            )

        self.device_repo.delete_device_user_association(association)
