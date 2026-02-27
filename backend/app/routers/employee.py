from typing import List
from datetime import date
from fastapi import APIRouter, Depends, BackgroundTasks
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

@router.get("/schedule-summary")
def get_schedule_summary(
    year: int,
    month: int,
    week_start: date,
    week_end: date,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Return planned hours for the current week and month (published schedule only)."""
    from datetime import datetime as dt, timedelta
    from sqlmodel import select
    from ..models import Schedule, ShiftDefinition

    month_start = date(year, month, 1)
    # last day of month
    if month == 12:
        month_end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(year, month + 1, 1) - timedelta(days=1)

    def _hours_for_range(start: date, end: date) -> float:
        schedules = session.exec(
            select(Schedule).where(
                Schedule.user_id == current_user.id,
                Schedule.date >= start,
                Schedule.date <= end,
                Schedule.is_published == True,
            )
        ).all()
        total = 0.0
        for s in schedules:
            shift = session.get(ShiftDefinition, s.shift_def_id)
            if shift:
                start_dt = dt.combine(date.today(), shift.start_time)
                end_dt = dt.combine(date.today(), shift.end_time)
                if end_dt < start_dt:
                    end_dt += timedelta(days=1)
                total += (end_dt - start_dt).seconds / 3600
        return round(total, 1)

    # Find last scheduled date in the month
    last_scheduled = session.exec(
        select(Schedule).where(
            Schedule.user_id == current_user.id,
            Schedule.date >= month_start,
            Schedule.date <= month_end,
            Schedule.is_published == True,
        ).order_by(Schedule.date.desc())  # type: ignore[arg-type]
    ).first()

    return {
        "week_hours": _hours_for_range(week_start, week_end),
        "month_hours": _hours_for_range(month_start, month_end),
        "last_scheduled_date": last_scheduled.date.isoformat() if last_scheduled else None,
        "month": month,
        "year": year,
    }


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
    background_tasks: BackgroundTasks,
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
    
    # Notify all managers
    from ..models import Notification, RoleSystem
    from ..services.push_service import PushService, send_push_to_tokens
    push_svc = PushService(session)
    managers = session.exec(select(User).where(User.role_system == RoleSystem.MANAGER)).all()
    
    # 1. Notify Managers
    for m in managers:
        title = "Nowa zmiana na Giełdzie"
        body = f"Pracownik {current_user.full_name} oddał zmianę w dniu {schedule.date} na giełdę."
        notif = Notification(
            user_id=m.id,
            title=title,
            body=body,
        )
        session.add(notif)
        
        tokens = push_svc._get_user_tokens(m.id)
        if tokens:
            background_tasks.add_task(send_push_to_tokens, tokens, title, body)
            
    # 2. Notify Eligible Employees (users with the required role, excluding the offerer)
    eligible_employees = session.exec(
        select(User).where(
            User.role_system == RoleSystem.EMPLOYEE,
            User.is_active == True,
            User.id != current_user.id
        )
    ).all()
    
    # Filter users who have the role required for this shift
    for emp in eligible_employees:
        emp_role_ids = [r.id for r in emp.job_roles] if hasattr(emp, 'job_roles') else []
        if schedule.role_id in emp_role_ids:
            emp_title = "Nowa zmiana do wzięcia!"
            emp_body = f"Pracownik {current_user.full_name} wystawił swoją zmianę na giełdę ({schedule.date})."
            
            # Create in-app notification
            emp_notif = Notification(
                user_id=emp.id,
                title=emp_title,
                body=emp_body,
            )
            session.add(emp_notif)
            
            # Create push notification
            emp_tokens = push_svc._get_user_tokens(emp.id)
            if emp_tokens:
                background_tasks.add_task(send_push_to_tokens, emp_tokens, emp_title, emp_body)
        
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

@router.get("/giveaways")
def get_open_giveaways_for_employee(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get all open shift giveaways the current employee can potentially claim."""
    from datetime import datetime, timedelta
    from ..models import Availability, AvailabilityStatus

    giveaways = session.exec(
        select(ShiftGiveaway).where(
            ShiftGiveaway.status == GiveawayStatus.OPEN,
            ShiftGiveaway.offered_by != current_user.id,
        )
    ).all()

    result = []
    for g in giveaways:
        schedule = g.schedule
        if not schedule:
            continue
        shift = session.get(ShiftDefinition, schedule.shift_def_id)
        role = session.get(JobRole, schedule.role_id) if schedule.role_id else None
        offerer = session.get(User, g.offered_by)

        # Skip past shifts
        if schedule.date < date.today():
            continue

        # Conflict detection: does current user already have a shift on this date?
        my_shifts_on_day = session.exec(
            select(Schedule).where(
                Schedule.user_id == current_user.id,
                Schedule.date == schedule.date,
                Schedule.is_published == True,
            )
        ).all()

        conflict_type = "none"  # none | overlap | same_day
        if shift:
            g_start = shift.start_time
            g_end = shift.end_time
            for ms in my_shifts_on_day:
                my_shift = session.get(ShiftDefinition, ms.shift_def_id)
                if not my_shift:
                    continue
                # Check overlap > 30 min
                from datetime import datetime as dt
                def to_minutes(t) -> int:
                    return t.hour * 60 + t.minute
                overlap_start = max(to_minutes(g_start), to_minutes(my_shift.start_time))
                overlap_end = min(to_minutes(g_end), to_minutes(my_shift.end_time))
                overlap = overlap_end - overlap_start
                if overlap > 30:
                    conflict_type = "overlap"
                    break
                else:
                    conflict_type = "same_day"

        # Availability hint
        avail = session.exec(
            select(Availability).where(
                Availability.user_id == current_user.id,
                Availability.date == schedule.date,
                Availability.shift_def_id == schedule.shift_def_id,
            )
        ).first()
        availability_hint = avail.status.value if avail else None

        result.append({
            "id": str(g.id),
            "schedule_id": str(schedule.id),
            "date": schedule.date.isoformat(),
            "shift_name": shift.name if shift else None,
            "role_name": role.name if role else None,
            "role_id": schedule.role_id,
            "start_time": shift.start_time.strftime("%H:%M") if shift else None,
            "end_time": shift.end_time.strftime("%H:%M") if shift else None,
            "offered_by_name": offerer.full_name if offerer else "Unknown",
            "conflict_type": conflict_type,
            "availability_hint": availability_hint,
            "created_at": g.created_at.isoformat(),
        })

    return result


@router.post("/giveaways/{giveaway_id}/claim")
def claim_giveaway(
    giveaway_id: UUID,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Employee claims an open giveaway shift."""
    giveaway = session.get(ShiftGiveaway, giveaway_id)
    if not giveaway:
        raise HTTPException(status_code=404, detail="Giveaway not found")
    if giveaway.status != GiveawayStatus.OPEN:
        raise HTTPException(status_code=400, detail="Giveaway is no longer open")
    if giveaway.offered_by == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot claim your own giveaway")

    schedule = giveaway.schedule
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule entry not found")

    shift = session.get(ShiftDefinition, schedule.shift_def_id)

    # Hard-block: overlap > 30 min
    if shift:
        my_shifts_on_day = session.exec(
            select(Schedule).where(
                Schedule.user_id == current_user.id,
                Schedule.date == schedule.date,
                Schedule.is_published == True,
            )
        ).all()
        def to_minutes(t) -> int:
            return t.hour * 60 + t.minute
        for ms in my_shifts_on_day:
            my_shift = session.get(ShiftDefinition, ms.shift_def_id)
            if not my_shift:
                continue
            overlap_start = max(to_minutes(shift.start_time), to_minutes(my_shift.start_time))
            overlap_end = min(to_minutes(shift.end_time), to_minutes(my_shift.end_time))
            if overlap_end - overlap_start > 30:
                raise HTTPException(
                    status_code=400,
                    detail="You already have a shift that overlaps with this one by more than 30 minutes"
                )

    # Reassign the schedule to the current user
    schedule.user_id = current_user.id
    session.add(schedule)

    # Mark giveaway as taken
    giveaway.status = GiveawayStatus.TAKEN
    giveaway.taken_by = current_user.id
    session.add(giveaway)
    
    from ..models import Notification, RoleSystem
    from ..services.push_service import PushService, send_push_to_tokens
    push_svc = PushService(session)
    
    # Notify original employee
    title = "Zmiana przejęta"
    body = f"Twoja zmiana z dnia {schedule.date} została przejęta przez {current_user.full_name}."
    notif = Notification(
        user_id=giveaway.offered_by,
        title=title,
        body=body,
    )
    session.add(notif)
    
    tokens = push_svc._get_user_tokens(giveaway.offered_by)
    if tokens:
        background_tasks.add_task(send_push_to_tokens, tokens, title, body)
    
    # Notify managers
    managers = session.exec(select(User).where(User.role_system == RoleSystem.MANAGER)).all()
    for m in managers:
        m_title = "Zmiana na Giełdzie przejęta"
        m_body = f"{current_user.full_name} wziął zmianę pracownika z dnia {schedule.date}."
        m_notif = Notification(
            user_id=m.id,
            title=m_title,
            body=m_body,
        )
        session.add(m_notif)
        
        m_tokens = push_svc._get_user_tokens(m.id)
        if m_tokens:
            background_tasks.add_task(send_push_to_tokens, m_tokens, m_title, m_body)
        
    session.commit()

    return {"status": "claimed", "schedule_id": str(schedule.id)}



from typing import Optional
from ..models import LeaveRequest, LeaveStatus
from ..schemas import LeaveRequestCreate, LeaveRequestResponse

@router.post("/leave-requests", response_model=LeaveRequestResponse, status_code=201)
def create_leave_request(
    request: LeaveRequestCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if request.start_date < date.today():
        raise HTTPException(status_code=400, detail="Cannot request leave in the past")
    
    # Check overlaps
    overlaps = session.exec(
        select(LeaveRequest).where(
            LeaveRequest.user_id == current_user.id,
            LeaveRequest.status.in_([LeaveStatus.PENDING, LeaveStatus.APPROVED]),
            LeaveRequest.start_date <= request.end_date,
            LeaveRequest.end_date >= request.start_date
        )
    ).first()
    if overlaps:
        raise HTTPException(status_code=400, detail="Leave request overlaps with an existing pending/approved request")

    new_req = LeaveRequest(
        user_id=current_user.id,
        start_date=request.start_date,
        end_date=request.end_date,
        reason=request.reason,
        status=LeaveStatus.PENDING
    )
    session.add(new_req)
    
    # Notify managers
    from ..models import Notification, RoleSystem
    from ..services.push_service import PushService, send_push_to_tokens
    push_svc = PushService(session)
    managers = session.exec(select(User).where(User.role_system == RoleSystem.MANAGER)).all()
    for m in managers:
        title = "Nowy wniosek urlopowy"
        body = f"Pracownik {current_user.full_name} złożył wniosek o urlop od {request.start_date} do {request.end_date}."
        notif = Notification(
            user_id=m.id,
            title=title,
            body=body,
        )
        session.add(notif)
        
        tokens = push_svc._get_user_tokens(m.id)
        if tokens:
            background_tasks.add_task(send_push_to_tokens, tokens, title, body)
        
    session.commit()
    session.refresh(new_req)

    return LeaveRequestResponse(
        id=new_req.id,
        user_id=new_req.user_id,
        user_name=current_user.full_name,
        start_date=new_req.start_date,
        end_date=new_req.end_date,
        reason=new_req.reason,
        status=str(new_req.status.value),
        created_at=new_req.created_at,
        reviewed_at=new_req.reviewed_at,
    )

@router.get("/leave-requests", response_model=List[LeaveRequestResponse])
def get_my_leave_requests(
    status: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    query = select(LeaveRequest).where(LeaveRequest.user_id == current_user.id)
    if status:
        query = query.where(LeaveRequest.status == LeaveStatus(status))
    query = query.order_by(LeaveRequest.start_date.desc())
    
    requests = session.exec(query).all()
    
    return [
        LeaveRequestResponse(
            id=r.id,
            user_id=r.user_id,
            user_name=current_user.full_name,
            start_date=r.start_date,
            end_date=r.end_date,
            reason=r.reason,
            status=str(r.status.value),
            created_at=r.created_at,
            reviewed_at=r.reviewed_at,
        ) for r in requests
    ]

@router.delete("/leave-requests/{request_id}")
def cancel_leave_request(
    request_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    req = session.get(LeaveRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if req.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this request")
    if req.status != LeaveStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only PENDING requests can be cancelled")
    
    req.status = LeaveStatus.CANCELLED
    session.add(req)
    session.commit()
    return {"status": "cancelled"}
