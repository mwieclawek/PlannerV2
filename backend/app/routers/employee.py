from typing import List
from datetime import date
from fastapi import APIRouter, Depends
from sqlmodel import Session
from ..database import get_session
from ..models import User, Availability
from ..auth_utils import get_current_user
from ..schemas import AvailabilityUpdate, EmployeeScheduleResponse
from ..services.employee_service import EmployeeService

router = APIRouter(prefix="/employee", tags=["employee"])

def get_employee_service(session: Session = Depends(get_session)) -> EmployeeService:
    return EmployeeService(session)

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

