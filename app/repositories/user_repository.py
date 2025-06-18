from sqlalchemy.orm import Session
from app.models import DBUser, UserRole, DBWorkingGroup, DBDeviceUser
from typing import Optional, List


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_username(self, username: str) -> Optional[DBUser]:
        return self.db.query(DBUser).filter(DBUser.username == username).first()

    def get_user_by_id(self, user_id: int) -> Optional[DBUser]:
        return self.db.query(DBUser).filter(DBUser.id == user_id).first()

    def create_user(self, user: DBUser) -> DBUser:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user(self, user: DBUser) -> DBUser:
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_user(self, user: DBUser):
        self.db.delete(user)
        self.db.commit()

    def get_users_by_group(self, group_id: int) -> List[DBUser]:
        # Obtener usuarios que son miembros de este grupo (a través de device_users)
        # Esto requiere un join con DBDeviceUser y DBDevice para encontrar el working_group_id
        return (
            self.db.query(DBUser)
            .join(DBDeviceUser)
            .join(DBDeviceUser.device)
            .filter(DBDeviceUser.device.has(working_group_id=group_id))
            .distinct()
            .all()
        )

    def get_admin_by_group_id(self, group_id: int) -> Optional[DBUser]:
        return (
            self.db.query(DBUser)
            .join(DBWorkingGroup)
            .filter(
                DBWorkingGroup.id == group_id,
                DBWorkingGroup.creator_id == DBUser.id,
                DBUser.role
                == UserRole.ADMIN,  # Aseguramos que el creador también sea el admin
            )
            .first()
        )
