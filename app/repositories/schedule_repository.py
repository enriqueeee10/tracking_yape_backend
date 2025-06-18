from sqlalchemy.orm import Session
from app.models import DBGroupSchedule, DBIndividualSchedule
from typing import Optional, List
from datetime import datetime


class ScheduleRepository:
    def __init__(self, db: Session):
        self.db = db

    # --- Group Schedules ---
    def create_group_schedule(self, schedule: DBGroupSchedule) -> DBGroupSchedule:
        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def get_group_schedules_by_group(self, group_id: int) -> List[DBGroupSchedule]:
        return (
            self.db.query(DBGroupSchedule)
            .filter(DBGroupSchedule.working_group_id == group_id)
            .all()
        )

    def get_group_schedule_by_id(self, schedule_id: int) -> Optional[DBGroupSchedule]:
        return (
            self.db.query(DBGroupSchedule)
            .filter(DBGroupSchedule.id == schedule_id)
            .first()
        )

    def update_group_schedule(self, schedule: DBGroupSchedule) -> DBGroupSchedule:
        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def delete_group_schedule(self, schedule: DBGroupSchedule):
        self.db.delete(schedule)
        self.db.commit()

    # --- Individual Schedules ---
    def create_individual_schedule(
        self, schedule: DBIndividualSchedule
    ) -> DBIndividualSchedule:
        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def get_individual_schedule_by_id(
        self, schedule_id: int
    ) -> Optional[DBIndividualSchedule]:
        return (
            self.db.query(DBIndividualSchedule)
            .filter(DBIndividualSchedule.id == schedule_id)
            .first()
        )

    def get_individual_schedules_for_device_user(
        self, device_user_id: int
    ) -> List[DBIndividualSchedule]:
        return (
            self.db.query(DBIndividualSchedule)
            .filter(DBIndividualSchedule.device_user_id == device_user_id)
            .all()
        )

    def get_individual_schedules_for_device(
        self, device_id: int
    ) -> List[DBIndividualSchedule]:
        return (
            self.db.query(DBIndividualSchedule)
            .filter(DBIndividualSchedule.device_id == device_id)
            .all()
        )

    def get_individual_schedules_for_user(
        self, user_id: int
    ) -> List[DBIndividualSchedule]:
        return (
            self.db.query(DBIndividualSchedule)
            .filter(DBIndividualSchedule.user_id == user_id)
            .all()
        )

    def update_individual_schedule(
        self, schedule: DBIndividualSchedule
    ) -> DBIndividualSchedule:
        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def delete_individual_schedule(self, schedule: DBIndividualSchedule):
        self.db.delete(schedule)
        self.db.commit()
