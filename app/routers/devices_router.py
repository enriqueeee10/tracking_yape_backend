from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    DeviceCreate,
    DeviceOut,
    DeviceUpdate,
    DeviceUserCreate,
    DeviceUserOut,
    UserOut,
)
from app.services.device_service import DeviceService
from app.auth import get_current_admin, get_current_active_user_in_group
from app.models import DBUser
from typing import List

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.post("/", response_model=DeviceOut)
async def create_device(
    device_data: DeviceCreate,
    db: Session = Depends(get_db),
    current_admin: DBUser = Depends(get_current_admin),
):
    """
    Registra un nuevo dispositivo y lo asocia a un grupo de trabajo. Solo accesible para administradores.
    """
    device_service = DeviceService(db)
    new_device = device_service.create_device(device_data, current_admin)
    return new_device


@router.get("/{device_id}", response_model=DeviceOut)
async def get_device_by_id(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user_in_group),
):
    """
    Obtiene los detalles de un dispositivo por su ID.
    Solo accesible para usuarios que pertenecen al mismo grupo del dispositivo.
    """
    device_service = DeviceService(db)
    device = device_service.get_device_by_id(device_id, current_user)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo no encontrado."
        )
    return device


@router.get("/group/{group_id}", response_model=List[DeviceOut])
async def get_devices_for_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user_in_group),
):
    """
    Obtiene todos los dispositivos asociados a un grupo de trabajo.
    Solo accesible para usuarios que pertenecen o son administradores de ese grupo.
    """
    device_service = DeviceService(db)
    devices = device_service.get_devices_for_group(group_id, current_user)
    return devices


@router.put("/{device_id}", response_model=DeviceOut)
async def update_device(
    device_id: int,
    device_data: DeviceUpdate,
    db: Session = Depends(get_db),
    current_admin: DBUser = Depends(get_current_admin),
):
    """
    Actualiza un dispositivo existente. Solo accesible para el administrador del grupo del dispositivo.
    """
    device_service = DeviceService(db)
    updated_device = device_service.update_device(device_id, device_data, current_admin)
    return updated_device


@router.post("/{device_id}/deactivate", response_model=DeviceOut)
async def deactivate_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_admin: DBUser = Depends(get_current_admin),
):
    """
    Desactiva un dispositivo. Solo accesible para el administrador del grupo del dispositivo.
    """
    device_service = DeviceService(db)
    deactivated_device = device_service.deactivate_device(device_id, current_admin)
    return deactivated_device


@router.post("/assign-user", response_model=DeviceUserOut)
async def assign_user_to_device(
    device_user_data: DeviceUserCreate,
    db: Session = Depends(get_db),
    current_admin: DBUser = Depends(get_current_admin),
):
    """
    Asigna un usuario a un dispositivo. Solo accesible para el administrador del grupo al que pertenece el dispositivo.
    """
    device_service = DeviceService(db)
    new_association = device_service.assign_user_to_device(
        device_user_data, current_admin
    )
    return new_association


@router.get("/{device_id}/assigned-users", response_model=List[UserOut])
async def get_users_assigned_to_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user_in_group),
):
    """
    Obtiene la lista de usuarios asignados a un dispositivo específico.
    Solo accesible para usuarios que pertenecen al mismo grupo del dispositivo.
    """
    device_service = DeviceService(db)
    users_assigned = device_service.get_users_assigned_to_device(
        device_id, current_user
    )
    return users_assigned


@router.delete(
    "/remove-user-assignment/{device_user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_user_from_device(
    device_user_id: int,
    db: Session = Depends(get_db),
    current_admin: DBUser = Depends(get_current_admin),
):
    """
    Remueve una asignación de usuario a dispositivo. Solo accesible para el administrador del grupo del dispositivo.
    """
    device_service = DeviceService(db)
    device_service.remove_user_from_device(device_user_id, current_admin)
    return {"message": "Asignación removida exitosamente."}
