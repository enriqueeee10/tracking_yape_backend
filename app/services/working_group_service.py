from sqlalchemy.orm import Session
from app.models import DBWorkingGroup, DBUser, UserRole
from app.schemas import WorkingGroupCreate, WorkingGroupOut
from app.repositories.working_group_repository import WorkingGroupRepository
from fastapi import HTTPException, status
from typing import Optional, List


class WorkingGroupService:
    def __init__(self, db: Session):
        self.group_repo = WorkingGroupRepository(db)
        self.db = db

    def create_group(
        self, group_data: WorkingGroupCreate, creator_id: int
    ) -> WorkingGroupOut:
        existing_group = self.group_repo.get_working_group_by_name(group_data.name)
        if existing_group:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre del grupo de trabajo ya está en uso.",
            )

        new_group = DBWorkingGroup(
            name=group_data.name,
            description=group_data.description,
            creator_id=creator_id,
        )
        created_group = self.group_repo.create_working_group(new_group)
        return WorkingGroupOut.model_validate(created_group)

    def get_group_by_id(self, group_id: int) -> Optional[WorkingGroupOut]:
        group = self.group_repo.get_working_group_by_id(group_id)
        if not group:
            return None
        return WorkingGroupOut.model_validate(group)

    def get_groups_by_creator(self, creator_id: int) -> List[WorkingGroupOut]:
        groups = self.group_repo.get_working_groups_by_creator(creator_id)
        return [WorkingGroupOut.model_validate(group) for group in groups]

    def update_group(
        self, group_id: int, group_data: WorkingGroupCreate, current_user_id: int
    ) -> WorkingGroupOut:
        existing_group = self.group_repo.get_working_group_by_id(group_id)
        if not existing_group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Grupo de trabajo no encontrado.",
            )

        # Solo el creador puede actualizar el grupo
        if existing_group.creator_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para actualizar este grupo.",
            )

        # Verificar si el nuevo nombre ya está en uso por otro grupo
        if group_data.name != existing_group.name:
            if self.group_repo.get_working_group_by_name(group_data.name):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El nuevo nombre del grupo de trabajo ya está en uso.",
                )

        existing_group.name = group_data.name
        existing_group.description = group_data.description
        existing_group.is_active = group_data.is_active

        updated_group = self.group_repo.update_working_group(existing_group)
        return WorkingGroupOut.model_validate(updated_group)

    def deactivate_group(self, group_id: int, current_user_id: int):
        group = self.group_repo.get_working_group_by_id(group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Grupo de trabajo no encontrado.",
            )

        if group.creator_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para desactivar este grupo.",
            )

        group.is_active = False
        self.group_repo.update_working_group(group)
