from sqlalchemy.orm import Session
from app.models import DBDevice, DBDeviceUser
from typing import Optional, List


class DeviceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_device_by_uid(self, device_uid: str) -> Optional[DBDevice]:
        return self.db.query(DBDevice).filter(DBDevice.device_uid == device_uid).first()

    def get_device_by_id(self, device_id: int) -> Optional[DBDevice]:
        return self.db.query(DBDevice).filter(DBDevice.id == device_id).first()

    def get_devices_by_group(self, group_id: int) -> List[DBDevice]:
        return (
            self.db.query(DBDevice).filter(DBDevice.working_group_id == group_id).all()
        )

    def create_device(self, device: DBDevice) -> DBDevice:
        self.db.add(device)
        self.db.commit()
        self.db.refresh(device)
        return device

    def update_device(self, device: DBDevice) -> DBDevice:
        self.db.commit()
        self.db.refresh(device)
        return device

    def delete_device(self, device: DBDevice):
        self.db.delete(device)
        self.db.commit()

    def create_device_user_association(self, device_user: DBDeviceUser) -> DBDeviceUser:
        self.db.add(device_user)
        self.db.commit()
        self.db.refresh(device_user)
        return device_user

    def get_device_user_association(
        self, user_id: int, device_id: int
    ) -> Optional[DBDeviceUser]:
        return (
            self.db.query(DBDeviceUser)
            .filter(
                DBDeviceUser.user_id == user_id, DBDeviceUser.device_id == device_id
            )
            .first()
        )

    def get_device_users_by_user(self, user_id: int) -> List[DBDeviceUser]:
        return self.db.query(DBDeviceUser).filter(DBDeviceUser.user_id == user_id).all()

    def get_device_users_by_device(self, device_id: int) -> List[DBDeviceUser]:
        return (
            self.db.query(DBDeviceUser)
            .filter(DBDeviceUser.device_id == device_id)
            .all()
        )

    def delete_device_user_association(self, device_user: DBDeviceUser):
        self.db.delete(device_user)
        self.db.commit()
