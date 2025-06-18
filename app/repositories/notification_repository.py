from sqlalchemy.orm import Session
from app.models import DBNotification, DBDeviceUserNotification
from typing import Optional, List
from datetime import datetime


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_notification(self, notification: DBNotification) -> DBNotification:
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def get_notification_by_id(self, notification_id: int) -> Optional[DBNotification]:
        return (
            self.db.query(DBNotification)
            .filter(DBNotification.id == notification_id)
            .first()
        )

    def get_notifications_by_group(
        self, group_id: int, skip: int = 0, limit: int = 100
    ) -> List[DBNotification]:
        return (
            self.db.query(DBNotification)
            .filter(DBNotification.working_group_id == group_id)
            .order_by(DBNotification.notification_timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_notification(self, notification: DBNotification) -> DBNotification:
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def get_device_user_notification(
        self, notification_id: int, device_id: int, user_id: int
    ) -> Optional[DBDeviceUserNotification]:
        return (
            self.db.query(DBDeviceUserNotification)
            .filter(
                DBDeviceUserNotification.notification_id == notification_id,
                DBDeviceUserNotification.device_id == device_id,
                DBDeviceUserNotification.user_id == user_id,
            )
            .first()
        )

    def create_device_user_notification(
        self, device_user_notification: DBDeviceUserNotification
    ) -> DBDeviceUserNotification:
        self.db.add(device_user_notification)
        self.db.commit()
        self.db.refresh(device_user_notification)
        return device_user_notification
