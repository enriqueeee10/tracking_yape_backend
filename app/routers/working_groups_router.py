from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import WorkingGroupCreate, WorkingGroupOut
from app.services.working_group_service import WorkingGroupService
from app.auth import get_current_admin
from app.models import DBUser
from typing import List

router = APIRouter(prefix="/groups", tags=["Working Groups"])


@router.post("/", response_model=WorkingGroupOut)
async def create_working_group(
    group_data: WorkingGroupCreate,
    db: Session = Depends(get_db),
    current_admin: DBUser = Depends(
        get_current_admin
    ),  # Solo el admin puede crear grupos
):
    """
    Crea un nuevo grupo de trabajo. Solo accesible para administradores.
    Nota: Normalmente, el grupo se crea al registrar un dueño, pero este endpoint permite crear grupos adicionales si es necesario.
    """
    group_service = WorkingGroupService(db)
    new_group = group_service.create_group(group_data, current_admin.id)
    return new_group


@router.get("/{group_id}", response_model=WorkingGroupOut)
async def get_working_group_by_id(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(
        get_current_admin
    ),  # Asumimos que solo el admin lo consulta para su grupo
):
    """
    Obtiene los detalles de un grupo de trabajo por su ID. Solo accesible para el creador del grupo.
    """
    group_service = WorkingGroupService(db)
    group = group_service.get_group_by_id(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grupo de trabajo no encontrado.",
        )

    # Si el usuario actual no es el creador del grupo, denegar acceso.
    if group.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver este grupo.",
        )

    return group


@router.get("/my-groups", response_model=List[WorkingGroupOut])
async def get_my_working_groups(
    db: Session = Depends(get_db),
    current_admin: DBUser = Depends(
        get_current_admin
    ),  # Solo el admin puede ver sus grupos
):
    """
    Obtiene todos los grupos de trabajo creados por el administrador actual.
    """
    group_service = WorkingGroupService(db)
    groups = group_service.get_groups_by_creator(current_admin.id)
    return groups


@router.put("/{group_id}", response_model=WorkingGroupOut)
async def update_working_group(
    group_id: int,
    group_data: WorkingGroupCreate,  # Usamos Create schema para la actualización parcial
    db: Session = Depends(get_db),
    current_admin: DBUser = Depends(get_current_admin),
):
    """
    Actualiza un grupo de trabajo existente. Solo accesible para el creador del grupo.
    """
    group_service = WorkingGroupService(db)
    updated_group = group_service.update_group(group_id, group_data, current_admin.id)
    return updated_group


@router.post("/{group_id}/deactivate", response_model=WorkingGroupOut)
async def deactivate_working_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_admin: DBUser = Depends(get_current_admin),
):
    """
    Desactiva un grupo de trabajo. Solo accesible para el creador del grupo.
    """
    group_service = WorkingGroupService(db)
    group_service.deactivate_group(group_id, current_admin.id)
    # Obtener el grupo actualizado para la respuesta
    deactivated_group = group_service.get_group_by_id(group_id)
    if not deactivated_group:  # Debería existir si la desactivación fue exitosa
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al recuperar el grupo desactivado.",
        )
    return deactivated_group
