from typing import List
from datetime import date
from uuid import UUID
from sqlmodel import Session, select
from ..models import Availability, Schedule, ShiftDefinition, JobRole
from ..schemas import AvailabilityUpdate

class EmployeeService:
    def __init__(self, session: Session):
        self.session = session

    def get_availability(self, user_id: UUID, start_date: date, end_date: date) -> List[Availability]:
        statement = select(Availability).where(
            Availability.user_id == user_id,
            Availability.date >= start_date,
            Availability.date <= end_date
        )
        return self.session.exec(statement).all()

    def update_availability(self, user_id: UUID, updates: List[AvailabilityUpdate]):
        for up in updates:
            existing = self.session.exec(select(Availability).where(
                Availability.user_id == user_id,
                Availability.date == up.date,
                Availability.shift_def_id == up.shift_def_id
            )).first()
            
            if existing:
                existing.status = up.status
                self.session.add(existing)
            else:
                new_avail = Availability(
                    user_id=user_id,
                    date=up.date,
                    shift_def_id=up.shift_def_id,
                    status=up.status
                )
                self.session.add(new_avail)
        
        self.session.commit()

    def get_schedule(self, user_id: UUID, start_date: date, end_date: date) -> List[dict]:
        statement = select(Schedule).where(
            Schedule.user_id == user_id,
            Schedule.date >= start_date,
            Schedule.date <= end_date,
            Schedule.is_published == True 
        )
        schedules = self.session.exec(statement).all()
        
        response = []
        for s in schedules:
            shift = self.session.get(ShiftDefinition, s.shift_def_id)
            response.append({
                "id": s.id,
                "date": s.date,
                "shift_name": shift.name if shift else "Unknown",
                "role_name": self.session.get(JobRole, s.role_id).name if s.role_id else "Unknown",
                "start_time": shift.start_time.isoformat() if shift and shift.start_time else "",
                "end_time": shift.end_time.isoformat() if shift and shift.end_time else ""
            })
        return response
