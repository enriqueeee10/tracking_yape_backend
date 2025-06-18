from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    GroupScheduleCreate,
    GroupScheduleOut,
    IndividualScheduleCreate,
    IndividualScheduleOut,
    ScheduleUpdate,
)
from app.services.schedule_service import ScheduleService
from app.auth import get_current_admin, get_current_active_user_in_group
from app.models import DBUser
from typing import List

router = APIRouter(prefix="/schedules", tags=["Schedules"])


# --- Group Schedules ---
@router.post("/group/{group_id}", response_model=GroupScheduleOut)
async def create_group_schedule(
    group_id: int,
    schedule_data: GroupScheduleCreate,
    db: Session = Depends(get_db),
    current_admin: DBUser = Depends(
        get_current_admin
    ),  # Solo admin puede crear horarios de grupo
):
    """
    Crea un nuevo horario para un grupo de trabajo. Solo accesible para administradores del grupo.
    """
    schedule_service = ScheduleService(db)
    new_schedule = schedule_service.create_group_schedule(
        schedule_data, group_id, current_admin
    )
    return new_schedule


@router.get("/group/{group_id}", response_model=List[GroupScheduleOut])
async def get_group_schedules(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user_in_group),
):
    """
    Obtiene todos los horarios para un grupo de trabajo.
    Accesible para usuarios (admin o miembro) que pertenecen a ese grupo.
    """
    schedule_service = ScheduleService(db)
    schedules = schedule_service.get_group_schedules(group_id, current_user)
    return schedules


@router.put("/group/{schedule_id}", response_model=GroupScheduleOut)
async def update_group_schedule(
    schedule_id: int,
    schedule_data: ScheduleUpdate,
    db: Session = Depends(get_db),
    current_admin: DBUser = Depends(get_current_admin),
):
    """
    Actualiza un horario de grupo existente. Solo accesible para el administrador del grupo.
    """
    schedule_service = ScheduleService(db)
    updated_schedule = schedule_service.update_group_schedule(
        schedule_id, schedule_data, current_admin
    )
    return updated_schedule


@router.delete("/group/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_admin: DBUser = Depends(get_current_admin),
):
    """
    Elimina un horario de grupo existente. Solo accesible para el administrador del grupo.
    """
    schedule_service = ScheduleService(db)
    schedule_service.delete_group_schedule(schedule_id, current_admin)
    return {"message": "Horario de grupo eliminado exitosamente."}


# --- Individual Schedules ---
@router.post("/individual", response_model=IndividualScheduleOut)
async def create_individual_schedule(
    schedule_data: IndividualScheduleCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(
        get_current_active_user_in_group
    ),  # Admin o el propio usuario
):
    """
    Crea un nuevo horario individual para un dispositivo_usuario, dispositivo o usuario.
    Solo accesible para administradores del grupo o el propio usuario para sus horarios.
    """
    schedule_service = ScheduleService(db)
    new_schedule = schedule_service.create_individual_schedule(
        schedule_data, current_user
    )
    return new_schedule


@router.get("/individual/{schedule_id}", response_model=IndividualScheduleOut)
async def get_individual_schedule_by_id(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user_in_group),
):
    """
    Obtiene los detalles de un horario individual por su ID.
    Accesible para administradores del grupo o el usuario/propietario.
    """
    schedule_service = ScheduleService(db)
    schedule = schedule_service.get_individual_schedule_by_id(schedule_id, current_user)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Horario individual no encontrado.",
        )
    return schedule


@router.put("/individual/{schedule_id}", response_model=IndividualScheduleOut)
async def update_individual_schedule(
    schedule_id: int,
    schedule_data: ScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user_in_group),
):
    """
    Actualiza un horario individual existente.
    Accesible para administradores del grupo o el propio usuario/propietario.
    """
    schedule_service = ScheduleService(db)
    updated_schedule = schedule_service.update_individual_schedule(
        schedule_id, schedule_data, current_user
    )
    return updated_schedule


@router.delete("/individual/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_individual_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user_in_group),
):
    """
    Elimina un horario individual existente.
    Accesible para administradores del grupo o el propio usuario/propietario.
    """
    schedule_service = ScheduleService(db)
    schedule_service.delete_individual_schedule(schedule_id, current_user)
    return {"message": "Horario individual eliminado exitosamente."}


@router.get("/user/{user_id}/individual", response_model=List[IndividualScheduleOut])
async def get_individual_schedules_for_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user_in_group),
):
    """
    Obtiene los horarios individuales para un usuario específico.
    Accesible para el propio usuario o un administrador de su grupo.
    """
    if user_id != current_user.id and current_user.role != DBUser.role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver los horarios de este usuario.",
        )

    # Si es admin, verificar que el user_id pertenezca a su grupo (opcional, dependiendo de la estrictez)
    # Por ahora, si es admin, puede ver cualquier usuario.

    schedule_service = ScheduleService(db)
    schedules = schedule_service.schedule_repo.get_individual_schedules_for_user(
        user_id
    )
    return [IndividualScheduleOut.model_validate(s) for s in schedules]


@router.get(
    "/device/{device_id}/individual", response_model=List[IndividualScheduleOut]
)
async def get_individual_schedules_for_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user_in_group),
):
    """
    Obtiene los horarios individuales para un dispositivo específico.
    Accesible para el propio usuario o un administrador de su grupo (si el dispositivo está en su grupo).
    """
    schedule_service = ScheduleService(db)
    device = schedule_service.device_repo.get_device_by_id(device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo no encontrado."
        )

    # Verificar si el usuario actual es admin del grupo del dispositivo, o un miembro de ese grupo.
    is_admin_of_group = current_user.role == DBUser.role.ADMIN and any(
        g.id == device.working_group_id for g in current_user.created_working_groups
    )
    is_member_of_group = any(
        du.device_id == device_id and du.user_id == current_user.id
        for du in current_user.user_devices
    )

    if not (is_admin_of_group or is_member_of_group):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver los horarios de este dispositivo.",
        )

    schedules = schedule_service.schedule_repo.get_individual_schedules_for_device(
        device_id
    )
    return [IndividualScheduleOut.model_validate(s) for s in schedules]
