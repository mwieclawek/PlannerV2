from typing import List
from datetime import date
from fastapi import APIRouter, Depends
from sqlmodel import Session
from ..database import get_session
from ..models import User, Availability
from ..auth_utils import get_current_user
from ..schemas import AvailabilityUpdate, EmployeeScheduleResponse, GoogleAuthRequest
from ..services.employee_service import EmployeeService

router = APIRouter(prefix="/employee", tags=["employee"])

def get_employee_service(session: Session = Depends(get_session)) -> EmployeeService:
    return EmployeeService(session)

@router.post("/google-calendar/auth")
def link_google_calendar(
    request: GoogleAuthRequest,
    current_user: User = Depends(get_current_user),
    service: EmployeeService = Depends(get_employee_service)
):
    service.link_google_calendar(current_user.id, request.auth_code)
    return {"status": "success", "message": "Google Calendar linked successfully"}

@router.get("/availability/status")
def check_availability_status(
    start_date: date, 
    end_date: date, 
    current_user: User = Depends(get_current_user), 
    service: EmployeeService = Depends(get_employee_service)
):
    """Check if the employee has submitted availability for the given date range"""
    availabilities = service.get_availability(current_user.id, start_date, end_date)
    return {"submitted": len(availabilities) > 0}

@router.get("/availability", response_model=List[Availability])
def get_my_availability(
    start_date: date, 
    end_date: date, 
    current_user: User = Depends(get_current_user), 
    service: EmployeeService = Depends(get_employee_service)
):
    return service.get_availability(current_user.id, start_date, end_date)

@router.post("/availability")
def update_availability(
    updates: List[AvailabilityUpdate],
    current_user: User = Depends(get_current_user),
    service: EmployeeService = Depends(get_employee_service)
):
    service.update_availability(current_user.id, updates)
    return {"status": "ok", "updated": len(updates)}

@router.get("/my-schedule", response_model=List[EmployeeScheduleResponse])
def get_my_schedule(
    start_date: date,
    end_date: date,
    current_user: User = Depends(get_current_user),
    service: EmployeeService = Depends(get_employee_service)
):
    return service.get_schedule(current_user.id, start_date, end_date)

# Attendance Endpoints
from datetime import datetime, time
from sqlmodel import select
from ..models import Attendance, AttendanceStatus, Schedule, ShiftDefinition

@router.get("/attendance/defaults/{target_date}")
def get_attendance_defaults(
    target_date: date,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get default check-in/out times from schedule for a given date"""
    schedule = session.exec(
        select(Schedule).where(
            Schedule.user_id == current_user.id,
            Schedule.date == target_date
        )
    ).first()
    
    if schedule:
        shift = session.get(ShiftDefinition, schedule.shift_def_id)
        return {
            "scheduled": True,
            "check_in": shift.start_time.strftime("%H:%M") if shift else None,
            "check_out": shift.end_time.strftime("%H:%M") if shift else None,
            "shift_name": shift.name if shift else None
        }
    return {"scheduled": False, "check_in": None, "check_out": None, "shift_name": None}

@router.post("/attendance")
def register_attendance(
    target_date: date,
    check_in: str,  # HH:MM
    check_out: str, # HH:MM
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Register employee attendance for a day"""
    # Check if already registered
    existing = session.exec(
        select(Attendance).where(
            Attendance.user_id == current_user.id,
            Attendance.date == target_date
        )
    ).first()
    
    if existing:
        return {"error": "Attendance already registered for this date"}
    
    # Check if was scheduled
    schedule = session.exec(
        select(Schedule).where(
            Schedule.user_id == current_user.id,
            Schedule.date == target_date
        )
    ).first()
    
    was_scheduled = schedule is not None
    status = AttendanceStatus.CONFIRMED if was_scheduled else AttendanceStatus.PENDING
    
    attendance = Attendance(
        user_id=current_user.id,
        date=target_date,
        check_in=datetime.strptime(check_in, "%H:%M").time(),
        check_out=datetime.strptime(check_out, "%H:%M").time(),
        was_scheduled=was_scheduled,
        status=status,
        schedule_id=schedule.id if schedule else None
    )
    session.add(attendance)
    session.commit()
    session.refresh(attendance)
    
    return {
        "id": str(attendance.id),
        "status": status.value,
        "was_scheduled": was_scheduled,
        "requires_approval": not was_scheduled
    }

@router.get("/attendance/my")
def get_my_attendance(
    start_date: date,
    end_date: date,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get employee's own attendance records"""
    attendances = session.exec(
        select(Attendance).where(
            Attendance.user_id == current_user.id,
            Attendance.date >= start_date,
            Attendance.date <= end_date
        )
    ).all()
    
    return [{
        "id": str(a.id),
        "date": a.date.isoformat(),
        "check_in": a.check_in.strftime("%H:%M"),
        "check_out": a.check_out.strftime("%H:%M"),
        "was_scheduled": a.was_scheduled,
        "status": a.status.value
    } for a in attendances]


# Shift Giveaway Endpoints
from uuid import UUID
from fastapi import HTTPException
from ..models import ShiftGiveaway, GiveawayStatus, JobRole

@router.post("/giveaway/{schedule_id}")
def offer_shift_giveaway(
    schedule_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Mark a shift as available for giveaway"""
    # Verify the schedule belongs to this user and is in the future
    schedule = session.exec(
        select(Schedule).where(
            Schedule.id == schedule_id,
            Schedule.user_id == current_user.id
        )
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule entry not found")
    
    if schedule.date < date.today():
        raise HTTPException(status_code=400, detail="Cannot give away past shifts")
    
    # Check if already offered
    existing = session.exec(
        select(ShiftGiveaway).where(
            ShiftGiveaway.schedule_id == schedule_id,
            ShiftGiveaway.status == GiveawayStatus.OPEN
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="This shift is already offered for giveaway")
    
    giveaway = ShiftGiveaway(
        schedule_id=schedule_id,
        offered_by=current_user.id,
    )
    session.add(giveaway)
    session.commit()
    session.refresh(giveaway)
    
    return {"id": str(giveaway.id), "status": "created"}

@router.delete("/giveaway/{giveaway_id}")
def cancel_giveaway(
    giveaway_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Cancel a giveaway offer"""
    giveaway = session.get(ShiftGiveaway, giveaway_id)
    
    if not giveaway:
        raise HTTPException(status_code=404, detail="Giveaway not found")
    
    if giveaway.offered_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not your giveaway")
    
    if giveaway.status != GiveawayStatus.OPEN:
        raise HTTPException(status_code=400, detail="Cannot cancel, giveaway already processed")
    
    giveaway.status = GiveawayStatus.CANCELLED
    session.add(giveaway)
    session.commit()
    
    return {"status": "cancelled"}

@router.get("/giveaways/my")
def get_my_giveaways(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get employee's own giveaway offers"""
    giveaways = session.exec(
        select(ShiftGiveaway).where(
            ShiftGiveaway.offered_by == current_user.id
        )
    ).all()
    
    result = []
    for g in giveaways:
        schedule = g.schedule
        shift = session.get(ShiftDefinition, schedule.shift_def_id) if schedule else None
        role = session.get(JobRole, schedule.role_id) if schedule else None
        
        result.append({
            "id": str(g.id),
            "schedule_id": str(g.schedule_id),
            "status": g.status.value,
            "date": schedule.date.isoformat() if schedule else None,
            "shift_name": shift.name if shift else None,
            "role_name": role.name if role else None,
            "start_time": shift.start_time.strftime("%H:%M") if shift else None,
            "end_time": shift.end_time.strftime("%H:%M") if shift else None,
            "created_at": g.created_at.isoformat(),
        })
    
    return result
