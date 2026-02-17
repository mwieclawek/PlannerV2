from datetime import date
from typing import List, Dict, Any
from uuid import UUID
from sqlmodel import Session, select
from ..models import Schedule, User, JobRole, ShiftDefinition
from ..schemas import BatchSaveRequest, ScheduleResponse

class SchedulerService:
    def __init__(self, session: Session):
        self.session = session

    def save_batch(self, batch: BatchSaveRequest) -> int:
        # 1. Clear existing in range
        statements = select(Schedule).where(
            Schedule.date >= batch.start_date, 
            Schedule.date <= batch.end_date
        )
        existing = self.session.exec(statements).all()
        
        # Handle linked Attendance records (set schedule_id to None) to avoid FK violation
        existing_ids = [e.id for e in existing]
        if existing_ids:
            from ..models import Attendance
            linked_attendances = self.session.exec(
                select(Attendance).where(Attendance.schedule_id.in_(existing_ids))
            ).all()
            for att in linked_attendances:
                att.schedule_id = None
                self.session.add(att)
            self.session.commit() # Commit updates to Attendance first
            
        for e in existing:
            self.session.delete(e)
        
        # 2. Add new items
        count = 0
        for item in batch.items:
            new_sched = Schedule(
                date=item.date,
                shift_def_id=item.shift_def_id,
                user_id=item.user_id,
                role_id=item.role_id,
                is_published=True  # Visible to employees immediately after save
            )
            self.session.add(new_sched)
            count += 1
        
        self.session.commit()
        return count

    def get_schedule_list(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        query = select(Schedule).where(
            Schedule.date >= start_date,
            Schedule.date <= end_date
        )
        schedules = self.session.exec(query).all()
        
        response = []
        # Optimization: fetch all roles/shifts/users once if needed, but for weekly scale this is fine
        for s in schedules:
            shift = self.session.get(ShiftDefinition, s.shift_def_id)
            response.append({
                "id": s.id,
                "date": s.date,
                "shift_def_id": s.shift_def_id,
                "user_id": s.user_id,
                "role_id": s.role_id,
                "is_published": s.is_published,
                "user_name": s.user.full_name if s.user else "Unknown",
                "role_name": self.session.get(JobRole, s.role_id).name if s.role_id else "?",
                "shift_name": shift.name if shift else "?",
                "start_time": shift.start_time if shift else None,
                "end_time": shift.end_time if shift else None
            })
        return response

    def publish_schedule(self, start_date: date, end_date: date) -> int:
        query = select(Schedule).where(
            Schedule.date >= start_date,
            Schedule.date <= end_date
        )
        schedules = self.session.exec(query).all()
        count = 0
        for s in schedules:
            s.is_published = True
            self.session.add(s)
            count += 1
        self.session.commit()
        return count
