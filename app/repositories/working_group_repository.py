from sqlalchemy.orm import Session
from app.models import DBWorkingGroup
from typing import Optional, List


class WorkingGroupRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_working_group_by_name(self, name: str) -> Optional[DBWorkingGroup]:
        return self.db.query(DBWorkingGroup).filter(DBWorkingGroup.name == name).first()

    def get_working_group_by_id(self, group_id: int) -> Optional[DBWorkingGroup]:
        return (
            self.db.query(DBWorkingGroup).filter(DBWorkingGroup.id == group_id).first()
        )

    def get_working_groups_by_creator(self, creator_id: int) -> List[DBWorkingGroup]:
        return (
            self.db.query(DBWorkingGroup)
            .filter(DBWorkingGroup.creator_id == creator_id)
            .all()
        )

    def create_working_group(self, working_group: DBWorkingGroup) -> DBWorkingGroup:
        self.db.add(working_group)
        self.db.commit()
        self.db.refresh(working_group)
        return working_group

    def update_working_group(self, working_group: DBWorkingGroup) -> DBWorkingGroup:
        self.db.commit()
        self.db.refresh(working_group)
        return working_group

    def delete_working_group(self, working_group: DBWorkingGroup):
        self.db.delete(working_group)
        self.db.commit()
