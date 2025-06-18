from sqlalchemy.orm import Session
from app.models import (
    DBNotification,
    NotificationStatus,
    DBUser,
    DBDevice,
    DBDeviceUser,
    DBDeviceUserNotification,
)
from app.schemas import NotificationCreate, NotificationOut, NotificationUpdateStatus
from app.repositories.notification_repository import NotificationRepository
from app.repositories.working_group_repository import WorkingGroupRepository
from app.repositories.device_repository import DeviceRepository
from app.repositories.user_repository import UserRepository
from fastapi import HTTPException, status
from typing import Optional, List
from datetime import datetime


class NotificationService:
    def __init__(self, db: Session):
        self.notification_repo = NotificationRepository(db)
        self.group_repo = WorkingGroupRepository(db)
        self.device_repo = DeviceRepository(db)
        self.user_repo = UserRepository(db)
        self.db = db

    def create_notification(
        self, notification_data: NotificationCreate, working_group_id: int
    ) -> NotificationOut:
        # Validar que el grupo exista
        group = self.group_repo.get_working_group_by_id(working_group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Grupo de trabajo no encontrado.",
            )

        new_notification = DBNotification(
            working_group_id=working_group_id,
            raw_notification=notification_data.raw_notification,
            name=notification_data.name,
            amount=notification_data.amount,
            security_code=notification_data.security_code,
            notification_timestamp=notification_data.notification_timestamp,
            status=NotificationStatus.RECEIVED,  # Estado inicial al recibir
        )
        created_notification = self.notification_repo.create_notification(
            new_notification
        )
        return NotificationOut.model_validate(created_notification)

    def get_notification_by_id(
        self, notification_id: int, current_user_group_id: int
    ) -> Optional[NotificationOut]:
        notification = self.notification_repo.get_notification_by_id(notification_id)
        if not notification:
            return None

        # Solo usuarios del mismo grupo pueden ver la notificación
        if notification.working_group_id != current_user_group_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para ver esta notificación.",
            )

        return NotificationOut.model_validate(notification)

    def get_notifications_for_group(
        self, group_id: int, current_user_id: int, skip: int = 0, limit: int = 100
    ) -> List[NotificationOut]:
        # Verificar que el usuario pertenezca o sea admin del grupo
        current_user = self.user_repo.get_user_by_id(current_user_id)
        is_admin_of_group = current_user.role == DBUser.role.ADMIN and any(
            g.id == group_id for g in current_user.created_working_groups
        )
        is_member_of_group = any(
            du.device.working_group_id == group_id for du in current_user.user_devices
        )  # Verifica pertenencia via device_users

        if not (is_admin_of_group or is_member_of_group):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para ver las notificaciones de este grupo.",
            )

        notifications = self.notification_repo.get_notifications_by_group(
            group_id, skip, limit
        )
        return [
            NotificationOut.model_validate(notification)
            for notification in notifications
        ]

    def update_notification_status(
        self,
        notification_id: int,
        status_data: NotificationUpdateStatus,
        current_user_id: int,
    ) -> NotificationOut:
        notification_to_update = self.notification_repo.get_notification_by_id(
            notification_id
        )
        if not notification_to_update:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notificación no encontrada.",
            )

        # Solo usuarios del grupo de la notificación pueden cambiar su estado
        current_user = self.user_repo.get_user_by_id(current_user_id)
        user_group_id = (
            current_user.created_working_groups[0].id
            if current_user.created_working_groups
            else (
                current_user.user_devices[0].device.working_group_id
                if current_user.user_devices
                else None
            )
        )

        if notification_to_update.working_group_id != user_group_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para actualizar esta notificación.",
            )

        notification_to_update.status = status_data.status
        updated_notification = self.notification_repo.update_notification(
            notification_to_update
        )
        return NotificationOut.model_validate(updated_notification)

    def register_sent_notification(
        self, notification_id: int, device_id: int, user_id: int
    ) -> DBDeviceUserNotification:
        # Verificar si ya se ha registrado este envío para evitar duplicados
        existing_record = self.notification_repo.get_device_user_notification(
            notification_id, device_id, user_id
        )
        if existing_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta notificación ya ha sido registrada como enviada a este dispositivo/usuario.",
            )

        # Verificar que la notificación, dispositivo y usuario existan
        notification = self.notification_repo.get_notification_by_id(notification_id)
        device = self.device_repo.get_device_by_id(device_id)
        user = self.user_repo.get_user_by_id(user_id)

        if not (notification and device and user):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notificación, dispositivo o usuario no encontrado.",
            )

        # Opcional: Podrías añadir una validación para asegurar que el user y device pertenecen al mismo grupo que la notificación

        new_record = DBDeviceUserNotification(
            notification_id=notification_id,
            device_id=device_id,
            user_id=user_id,
            sent_at=datetime.utcnow(),  # Registra el momento del envío
        )
        created_record = self.notification_repo.create_device_user_notification(
            new_record
        )
        return created_record
