from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    NotificationCreate,
    NotificationOut,
    NotificationUpdateStatus,
    DeviceUserNotificationCreate,
    DeviceUserNotificationOut,
)
from app.services.notification_service import NotificationService
from app.auth import get_current_active_user_in_group
from app.models import DBUser
from typing import List

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("/incoming", response_model=NotificationOut)
async def receive_notification_from_client(
    notification_data: NotificationCreate,
    db: Session = Depends(get_db),
    # Aquí podríamos tener una autenticación simplificada para el servicio Kotlin,
    # como una clave API o un token de alcance limitado específico para notificaciones.
    # Por ahora, para la demo, usaremos un "user" especial o un ID de grupo directo.
    # Supongamos que el cliente Kotlin envía el working_group_id para el cual es la notificación.
    # O, si el cliente Kotlin se autentica como un usuario específico de un grupo:
    # current_user: DBUser = Depends(get_current_active_user_in_group)
    # Para el servicio de Kotlin, el `working_group_id` debería ser parte del payload o de un token específico.
    # Por ahora, lo recibiremos en el payload para simplificar la integración con Kotlin,
    # o si el token del servicio Android tiene el `working_group_id`.
    # Si se envía desde un ESP32, se enviaría el device_uid, y el backend lo mapearía al group_id.
    # Para la integración con el servicio Kotlin, necesitamos que el token del servicio Kotlin
    # contenga el working_group_id. Así que lo obtendremos de un usuario autenticado.
    current_user: DBUser = Depends(
        get_current_active_user_in_group
    ),  # Asumimos que el servicio Kotlin usa un usuario autenticado
):
    """
    Recibe una notificación de YAPE del servicio cliente (Kotlin/ESP32).
    """
    notification_service = NotificationService(db)

    # Obtener el working_group_id del usuario autenticado del servicio Kotlin
    user_group_id = (
        current_user.created_working_groups[0].id
        if current_user.created_working_groups
        else None
    )
    if user_group_id is None and current_user.user_devices:
        user_group_id = current_user.user_devices[0].device.working_group.id

    if user_group_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario autenticado no está asociado a un grupo de trabajo para recibir notificaciones.",
        )

    new_notification = notification_service.create_notification(
        notification_data, user_group_id
    )
    return new_notification


@router.get("/group/{group_id}", response_model=List[NotificationOut])
async def get_notifications_for_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user_in_group),
    skip: int = 0,
    limit: int = 100,
):
    """
    Obtiene todas las notificaciones para un grupo de trabajo específico.
    Solo accesible para usuarios que pertenecen o son administradores de ese grupo.
    """
    notification_service = NotificationService(db)
    notifications = notification_service.get_notifications_for_group(
        group_id, current_user.id, skip, limit
    )
    return notifications


@router.patch("/{notification_id}/status", response_model=NotificationOut)
async def update_notification_status(
    notification_id: int,
    status_data: NotificationUpdateStatus,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(
        get_current_active_user_in_group
    ),  # Cualquier usuario del grupo puede marcar el estado
):
    """
    Actualiza el estado de una notificación (ej. de 'received' a 'sent').
    """
    notification_service = NotificationService(db)
    updated_notification = notification_service.update_notification_status(
        notification_id, status_data, current_user.id
    )
    return updated_notification


@router.post("/sent-register", response_model=DeviceUserNotificationOut)
async def register_sent_notification(
    data: DeviceUserNotificationCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(
        get_current_active_user_in_group
    ),  # Puede ser el usuario que recibe (via MQTT) o un servicio interno
):
    """
    Registra que una notificación específica fue enviada a un dispositivo/usuario específico.
    Esto se usa para la deduplicación y tracking.
    """
    # Se podría añadir validación para asegurar que el current_user tiene permisos
    # sobre la notificación/dispositivo/usuario en cuestión.
    notification_service = NotificationService(db)
    record = notification_service.register_sent_notification(
        data.notification_id, data.device_id, data.user_id
    )
    return record
