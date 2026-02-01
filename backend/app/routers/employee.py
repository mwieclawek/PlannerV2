from typing import List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ..database import get_session
from ..models import User, Availability, AvailabilityStatus
from ..auth_utils import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/employee", tags=["employee"])

class AvailabilityUpdate(BaseModel):
    date: date
    shift_def_id: int
    status: AvailabilityStatus

@router.get("/availability", response_model=List[Availability])
def get_my_availability(
    start_date: date, 
    end_date: date, 
    current_user: User = Depends(get_current_user), 
    session: Session = Depends(get_session)
):
    statement = select(Availability).where(
        Availability.user_id == current_user.id,
        Availability.date >= start_date,
        Availability.date <= end_date
    )
    return session.exec(statement).all()

@router.post("/availability")
def update_availability(
    updates: List[AvailabilityUpdate],
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    results = []
    for up in updates:
        existing = session.exec(select(Availability).where(
            Availability.user_id == current_user.id,
            Availability.date == up.date,
            Availability.shift_def_id == up.shift_def_id
        )).first()
        
        if existing:
            existing.status = up.status
            session.add(existing)
        else:
            new_avail = Availability(
                user_id=current_user.id,
                date=up.date,
                shift_def_id=up.shift_def_id,
                status=up.status
            )
            session.add(new_avail)
    
    session.commit()
    return {"status": "ok", "updated": len(updates)}

@router.get("/my-schedule")
def get_my_schedule(
    start_date: date,
    end_date: date,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    from ..models import Schedule, ShiftDefinition, JobRole
    
    # Only show published schedules? 
    # For now, let's show all for testing simplicity, or respect 'is_published'
    # "is_published" usually means manager is done editing.
    
    statement = select(Schedule).where(
        Schedule.user_id == current_user.id,
        Schedule.date >= start_date,
        Schedule.date <= end_date,
        Schedule.is_published == True 
    )
    schedules = session.exec(statement).all()
    
    response = []
    for s in schedules:
        shift = session.get(ShiftDefinition, s.shift_def_id)
        response.append({
            "id": s.id,
            "date": s.date,
            "shift_name": shift.name,
            "role_name": session.get(JobRole, s.role_id).name,
            "start_time": shift.start_time.isoformat() if shift.start_time else "",
            "end_time": shift.end_time.isoformat() if shift.end_time else ""
        })
    return response
