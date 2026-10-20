from typing import List, Optional
from uuid import UUID
from datetime import date
import logging
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlmodel import Session
from ..database import get_session
from ..models import User, Availability
from ..auth_utils import get_current_user
from ..schemas import AvailabilityUpdate, EmployeeScheduleResponse, GoogleAuthRequest, ScheduleResponse
from ..services.employee_service import EmployeeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/employee", tags=["employee"])

from ..tenant_context import require_tenant

def get_employee_service(
    session: Session = Depends(get_session),
    tenant_id: int = Depends(require_tenant),
) -> EmployeeService:
    return EmployeeService(session, tenant_id)

from ..services.google_calendar_service import GoogleCalendarService

@router.post("/google-calendar/auth")
def link_google_calendar(
    request: GoogleAuthRequest,
    current_user: User = Depends(get_current_user),
    service: EmployeeService = Depends(get_employee_service),
    session: Session = Depends(get_session)
):
    service.link_google_calendar(current_user.id, request.auth_code)
    # Immediately sync current and upcoming shifts to the connected calendar
    cal_service = GoogleCalendarService(session)
    sync_result = cal_service.sync_user_schedules(current_user.id, tenant_id=current_user.tenant_id)
    return {
        "status": "success",
        "message": "Google Calendar linked successfully",
        "synced": sync_result.get("synced", 0)
    }

@router.post("/google-calendar/sync")
def sync_google_calendar(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    cal_service = GoogleCalendarService(session)
    result = cal_service.sync_user_schedules(current_user.id, tenant_id=current_user.tenant_id)
    return result

@router.get("/google-calendar/status")
def get_google_calendar_status(
    current_user: User = Depends(get_current_user),
    service: EmployeeService = Depends(get_employee_service)
):
    return service.get_google_calendar_status(current_user.id)

@router.delete("/google-calendar/auth")
def unlink_google_calendar(
    current_user: User = Depends(get_current_user),
    service: EmployeeService = Depends(get_employee_service)
):
    service.unlink_google_calendar(current_user.id)
    return {"status": "success", "message": "Google Calendar unlinked successfully"}

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

@router.get("/schedules/all", response_model=List[ScheduleResponse])
def get_schedules_all(
    start_date: date,
    end_date: date,
    current_user: User = Depends(get_current_user),
    service: EmployeeService = Depends(get_employee_service)
):
    """Get the full team schedule for the given date range"""
    return service.get_team_schedule(start_date, end_date)

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
from datetime import datetime, time, timedelta
from sqlmodel import select
from ..models import Attendance, AttendanceStatus, Schedule, ShiftDefinition, RestaurantConfig, JobRole, Notification

def check_and_notify_overdue_attendances(
    session: Session,
    tenant_id: Optional[int],
    background_tasks: Optional[BackgroundTasks] = None,
) -> int:
    """
    When RestaurantConfig.require_attendance_registration is True, check published shifts
    that ended at least 30 minutes ago (and are on/after attendance_required_from) without
    an Attendance record. Send a one-time reminder Notification + Push to the employee.
    """
    if not tenant_id:
        return 0
    config = session.get(RestaurantConfig, tenant_id)
    if not config or not config.require_attendance_registration:
        return 0

    try:
        from ..services.google_calendar_service import WARSAW_TZ
        now_local = datetime.now(WARSAW_TZ).replace(tzinfo=None)
    except Exception:
        now_local = datetime.now()

    today = now_local.date()
    min_date = config.attendance_required_from or (today - timedelta(days=7))
    if min_date > today:
        return 0

    schedules = session.exec(
        select(Schedule)
        .join(User, Schedule.user_id == User.id)
        .where(
            User.tenant_id == tenant_id,
            User.is_active == True,
            Schedule.is_published == True,
            Schedule.date >= min_date,
            Schedule.date <= today,
        )
    ).all()

    if not schedules:
        return 0

    from ..services.push_service import PushService, send_push_to_tokens
    push_svc = PushService(session)
    notified_count = 0

    for sch in schedules:
        existing_att = session.exec(
            select(Attendance).where(
                Attendance.user_id == sch.user_id,
                Attendance.date == sch.date,
            )
        ).first()
        if existing_att:
            continue

        shift = session.get(ShiftDefinition, sch.shift_def_id)
        if not shift:
            continue

        start_dt = datetime.combine(sch.date, shift.start_time)
        end_dt = datetime.combine(sch.date, shift.end_time)
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)

        if now_local < end_dt + timedelta(minutes=30):
            continue

        date_str = sch.date.isoformat()
        title = "Przypomnienie o rejestracji czasu pracy"
        # Check deduplication so we only send once per shift date
        already_notified = session.exec(
            select(Notification).where(
                Notification.user_id == sch.user_id,
                Notification.title == title,
                Notification.body.contains(date_str),
            )
        ).first()
        if already_notified:
            continue

        body = (
            f"Minęło ponad 30 minut od zakończenia Twojej zmiany ({shift.name} w dniu {date_str}). "
            f"Zarejestruj swoją obecność lub zgłoś nieobecność w aplikacji."
        )
        notif = Notification(
            user_id=sch.user_id,
            title=title,
            body=body,
        )
        session.add(notif)
        notified_count += 1

        tokens = push_svc._get_user_tokens(sch.user_id)
        if tokens:
            if background_tasks is not None:
                background_tasks.add_task(send_push_to_tokens, tokens, title, body)
            else:
                send_push_to_tokens(tokens, title, body)

    if notified_count > 0:
        session.commit()
    return notified_count


@router.get("/config")
def get_employee_restaurant_config(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get restaurant feature flags and configuration relevant to the employee panel."""
    config = session.get(RestaurantConfig, current_user.tenant_id) if current_user.tenant_id else None
    if not config:
        config = session.exec(select(RestaurantConfig)).first()
    if not config:
        return {
            "name": "Restauracja",
            "require_attendance_registration": False,
            "attendance_required_from": None,
            "require_checklists": True,
            "enable_tip_pool": True,
            "enable_daily_closeout": True,
            "pos_enabled": False,
        }
    return {
        "id": config.id,
        "name": config.name,
        "require_attendance_registration": bool(config.require_attendance_registration),
        "attendance_required_from": config.attendance_required_from.isoformat() if config.attendance_required_from else None,
        "require_checklists": bool(getattr(config, "require_checklists", True)),
        "enable_tip_pool": bool(config.enable_tip_pool),
        "enable_daily_closeout": bool(getattr(config, "enable_daily_closeout", True)),
        "pos_enabled": bool(config.pos_enabled),
    }


@router.get("/attendance/missing")
def get_missing_attendance(
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Return published shifts of current_user that have already ended (or are in the past)
    and do not have an Attendance registration yet, respecting attendance_required_from.
    Also triggers the 30-minute post-shift reminder notification check.
    """
    check_and_notify_overdue_attendances(session, current_user.tenant_id, background_tasks)

    config = session.get(RestaurantConfig, current_user.tenant_id) if current_user.tenant_id else None
    if not config:
        config = session.exec(select(RestaurantConfig)).first()

    require_reg = bool(config.require_attendance_registration) if config else False
    req_from = config.attendance_required_from if config else None

    try:
        from ..services.google_calendar_service import WARSAW_TZ
        now_local = datetime.now(WARSAW_TZ).replace(tzinfo=None)
    except Exception:
        now_local = datetime.now()

    today = now_local.date()
    min_date = req_from if req_from else (today - timedelta(days=14))

    if min_date > today:
        return {
            "require_attendance_registration": require_reg,
            "attendance_required_from": req_from.isoformat() if req_from else None,
            "missing": [],
        }

    schedules = session.exec(
        select(Schedule).where(
            Schedule.user_id == current_user.id,
            Schedule.is_published == True,
            Schedule.date >= min_date,
            Schedule.date <= today,
        ).order_by(Schedule.date.desc())
    ).all()

    attendances = session.exec(
        select(Attendance).where(
            Attendance.user_id == current_user.id,
            Attendance.date >= min_date,
            Attendance.date <= today,
        )
    ).all()
    attended_dates = {a.date for a in attendances}

    missing_list = []
    seen_dates = set()
    for sch in schedules:
        if sch.date in attended_dates or sch.date in seen_dates:
            continue
        shift = session.get(ShiftDefinition, sch.shift_def_id)
        if not shift:
            continue

        start_dt = datetime.combine(sch.date, shift.start_time)
        end_dt = datetime.combine(sch.date, shift.end_time)
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)

        # Include if shift is on a past date OR if today's shift has already ended
        if sch.date < today or now_local >= end_dt:
            role = session.get(JobRole, sch.role_id) if sch.role_id else None
            seen_dates.add(sch.date)
            missing_list.append({
                "schedule_id": str(sch.id),
                "date": sch.date.isoformat(),
                "shift_name": shift.name,
                "role_name": role.name if role else "Pracownik",
                "start_time": shift.start_time.strftime("%H:%M"),
                "end_time": shift.end_time.strftime("%H:%M"),
                "overdue_30min": now_local >= (end_dt + timedelta(minutes=30)),
            })

    return {
        "require_attendance_registration": require_reg,
        "attendance_required_from": req_from.isoformat() if req_from else None,
        "missing": missing_list,
    }


@router.get("/attendance/defaults/{target_date}")
def get_attendance_defaults(
    target_date: date,
    service: EmployeeService = Depends(get_employee_service),
    current_user: User = Depends(get_current_user),
):
    """Get default check-in/out times from schedule for a given date"""
    return service.get_attendance_defaults(current_user, target_date)


@router.post("/attendance")
def register_attendance(
    target_date: date,
    check_in: str = "00:00",  # HH:MM
    check_out: str = "00:00",  # HH:MM
    checklist_skip_reason: Optional[str] = None,
    is_absent: bool = False,
    absence_reason: Optional[str] = None,
    service: EmployeeService = Depends(get_employee_service),
    current_user: User = Depends(get_current_user),
):
    """Register employee attendance (or absence on a scheduled shift) for a day"""
    return service.register_attendance(
        current_user=current_user,
        target_date=target_date,
        check_in=check_in,
        check_out=check_out,
        checklist_skip_reason=checklist_skip_reason,
        is_absent=is_absent,
        absence_reason=absence_reason,
    )


@router.get("/attendance/my")
def get_my_attendance(
    start_date: date,
    end_date: date,
    service: EmployeeService = Depends(get_employee_service),
    current_user: User = Depends(get_current_user),
):
    """Get employee's own attendance records"""
    return service.get_my_attendance(current_user, start_date, end_date)


# Shift Giveaway Endpoints
from uuid import UUID
from fastapi import HTTPException
from ..models import ShiftGiveaway, GiveawayStatus, JobRole, ShiftRoleLink
from ..schemas import OfferGiveawayRequest

def find_shift_conflict(
    session: Session,
    user_id: UUID,
    date_val: date,
    shift_def_id: int,
    exclude_schedule_id: Optional[UUID] = None
) -> Optional[tuple[Schedule, ShiftDefinition]]:
    """Check if the user already has an active schedule on date_val overlapping with shift_def_id."""
    from datetime import datetime as dt, timedelta
    target_def = session.get(ShiftDefinition, shift_def_id)
    if not target_def or not target_def.start_time or not target_def.end_time:
        return None

    existing_schedules = session.exec(
        select(Schedule).where(
            Schedule.user_id == user_id,
            Schedule.date == date_val,
            Schedule.id != exclude_schedule_id
        )
    ).all()

    start1 = dt.combine(date_val, target_def.start_time)
    end1 = dt.combine(date_val, target_def.end_time)
    if end1 <= start1:
        end1 += timedelta(days=1)

    for s in existing_schedules:
        s_def = session.get(ShiftDefinition, s.shift_def_id)
        if not s_def or not s_def.start_time or not s_def.end_time:
            continue
        start2 = dt.combine(date_val, s_def.start_time)
        end2 = dt.combine(date_val, s_def.end_time)
        if end2 <= start2:
            end2 += timedelta(days=1)

        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)
        if overlap_start < overlap_end:
            overlap_duration = (overlap_end - overlap_start).total_seconds() / 60.0
            is_enveloped = (start1 <= start2 and end1 >= end2) or (start2 <= start1 and end2 >= end1)
            if overlap_duration > 30 or is_enveloped:
                return (s, s_def)
    return None

@router.get("/giveaways/validate-swap")
def validate_shift_swap(
    offered_schedule_id: UUID,
    target_schedule_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Validate whether current_user can propose exchanging offered_schedule for target_schedule."""
    schedule = session.exec(
        select(Schedule).where(
            Schedule.id == offered_schedule_id,
            Schedule.user_id == current_user.id
        )
    ).first()
    if not schedule:
        return {"can_swap": False, "reason": "Nie znaleziono Twojej zmiany."}

    if schedule.date < date.today():
        return {"can_swap": False, "reason": "Nie można wymieniać zmian z przeszłości."}

    existing = session.exec(
        select(ShiftGiveaway).where(
            ShiftGiveaway.schedule_id == offered_schedule_id,
            ShiftGiveaway.status == GiveawayStatus.OPEN
        )
    ).first()
    if existing:
        return {"can_swap": False, "reason": "Ta zmiana została już wystawiona na giełdę."}

    target_schedule = session.get(Schedule, target_schedule_id)
    if not target_schedule:
        return {"can_swap": False, "reason": "Nie znaleziono docelowej zmiany współpracownika."}

    if target_schedule.user_id == current_user.id:
        return {"can_swap": False, "reason": "Nie możesz wymienić zmiany ze swoją własną zmianą."}

    target_user = session.get(User, target_schedule.user_id)
    if not target_user or target_user.tenant_id != current_user.tenant_id:
        return {"can_swap": False, "reason": "Współpracownik nie należy do tej samej restauracji."}

    # Validate roles
    user_a_role_ids = {r.id for r in current_user.job_roles}
    user_b_role_ids = {r.id for r in target_user.job_roles}

    target_role = session.get(JobRole, target_schedule.role_id) if target_schedule.role_id else None
    offered_role = session.get(JobRole, schedule.role_id) if schedule.role_id else None

    if target_schedule.role_id not in user_a_role_ids:
        role_label = target_role.name if target_role else "wymaganej"
        return {"can_swap": False, "reason": f"Nie posiadasz roli {role_label} wymaganej do przejęcia tej zmiany."}

    if schedule.role_id not in user_b_role_ids:
        role_label = offered_role.name if offered_role else "wymaganej"
        return {"can_swap": False, "reason": f"Pracownik {target_user.full_name} nie posiada roli {role_label} do Twojej zmiany."}

    # Check shift definition allowed roles
    allowed_a = set(session.exec(select(ShiftRoleLink.role_id).where(ShiftRoleLink.shift_def_id == schedule.shift_def_id)).all())
    if allowed_a and schedule.role_id not in allowed_a:
        return {"can_swap": False, "reason": "Niedozwolona rola dla Twojej zmiany."}

    allowed_b = set(session.exec(select(ShiftRoleLink.role_id).where(ShiftRoleLink.shift_def_id == target_schedule.shift_def_id)).all())
    if allowed_b and target_schedule.role_id not in allowed_b:
        return {"can_swap": False, "reason": "Niedozwolona rola dla zmiany współpracownika."}

    # Check overlaps
    conflict_b = find_shift_conflict(session, target_user.id, schedule.date, schedule.shift_def_id, exclude_schedule_id=target_schedule.id)
    if conflict_b:
        _, c_def = conflict_b
        return {
            "can_swap": False,
            "reason": f"Pracownik {target_user.full_name} ma już inną zmianę w tym czasie ({c_def.name} {c_def.start_time.strftime('%H:%M')}-{c_def.end_time.strftime('%H:%M')})."
        }

    conflict_a = find_shift_conflict(session, current_user.id, target_schedule.date, target_schedule.shift_def_id, exclude_schedule_id=schedule.id)
    if conflict_a:
        _, c_def = conflict_a
        return {
            "can_swap": False,
            "reason": f"Masz już inną zmianę w tym czasie ({c_def.name} {c_def.start_time.strftime('%H:%M')}-{c_def.end_time.strftime('%H:%M')})."
        }

    offered_def = session.get(ShiftDefinition, schedule.shift_def_id)
    target_def = session.get(ShiftDefinition, target_schedule.shift_def_id)

    return {
        "can_swap": True,
        "reason": None,
        "target_user_name": target_user.full_name,
        "target_shift_name": target_def.name if target_def else "",
        "offered_shift_name": offered_def.name if offered_def else ""
    }

@router.post("/giveaway/{schedule_id}")
def offer_shift_giveaway(
    schedule_id: UUID,
    background_tasks: BackgroundTasks,
    payload: Optional[OfferGiveawayRequest] = None,
    target_shift_id: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Mark a shift as available for giveaway or direct swap"""
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

    resolved_target_id = None
    target_schedule = None
    target_user = None
    if payload and payload.target_shift_id:
        resolved_target_id = str(payload.target_shift_id)
    elif target_shift_id:
        resolved_target_id = str(target_shift_id)

    if resolved_target_id:
        try:
            target_uuid = UUID(resolved_target_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid target shift id")

        target_schedule = session.get(Schedule, target_uuid)
        if not target_schedule:
            raise HTTPException(status_code=404, detail="Target shift not found")
        if target_schedule.user_id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot swap with your own shift")

        target_user = session.get(User, target_schedule.user_id)
        if not target_user or target_user.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=404, detail="Target user not found")

        # Validate matching roles
        user_a_role_ids = {r.id for r in current_user.job_roles}
        user_b_role_ids = {r.id for r in target_user.job_roles}

        if target_schedule.role_id not in user_a_role_ids:
            raise HTTPException(status_code=400, detail="Employees do not have matching roles for shift swap")
        if schedule.role_id not in user_b_role_ids:
            raise HTTPException(status_code=400, detail="Employees do not have matching roles for shift swap")

        allowed_a = set(session.exec(select(ShiftRoleLink.role_id).where(ShiftRoleLink.shift_def_id == schedule.shift_def_id)).all())
        if allowed_a and schedule.role_id not in allowed_a:
            raise HTTPException(status_code=400, detail="Employees do not have matching roles for shift swap")

        allowed_b = set(session.exec(select(ShiftRoleLink.role_id).where(ShiftRoleLink.shift_def_id == target_schedule.shift_def_id)).all())
        if allowed_b and target_schedule.role_id not in allowed_b:
            raise HTTPException(status_code=400, detail="Employees do not have matching roles for shift swap")

        # Check shift overlaps/collisions
        conflict_b = find_shift_conflict(session, target_user.id, schedule.date, schedule.shift_def_id, exclude_schedule_id=target_schedule.id)
        if conflict_b:
            _, c_def = conflict_b
            raise HTTPException(
                status_code=400,
                detail=f"Pracownik {target_user.full_name} ma już zaplanowaną inną zmianę w tym czasie ({c_def.name} {c_def.start_time.strftime('%H:%M')}-{c_def.end_time.strftime('%H:%M')})"
            )

        conflict_a = find_shift_conflict(session, current_user.id, target_schedule.date, target_schedule.shift_def_id, exclude_schedule_id=schedule.id)
        if conflict_a:
            _, c_def = conflict_a
            raise HTTPException(
                status_code=400,
                detail=f"Masz już zaplanowaną inną zmianę w tym czasie ({c_def.name} {c_def.start_time.strftime('%H:%M')}-{c_def.end_time.strftime('%H:%M')})"
            )

    giveaway = ShiftGiveaway(
        schedule_id=schedule_id,
        offered_by=current_user.id,
        target_shift_id=str(target_schedule.id) if target_schedule else None,
    )
    session.add(giveaway)
    
    # 1. Notify Managers
    from ..models import Notification, RoleSystem
    from ..services.push_service import PushService, send_push_to_tokens
    push_svc = PushService(session)
    managers = session.exec(select(User).where(User.role_system == RoleSystem.MANAGER, User.tenant_id == current_user.tenant_id)).all()
    
    for m in managers:
        if target_schedule:
            m_target_user = session.get(User, target_schedule.user_id)
            target_name = m_target_user.full_name if m_target_user else "innym pracownikiem"
            title = "Propozycja wymiany zmiany"
            body = f"Pracownik {current_user.full_name} zaproponował wymianę zmiany ze zmianą pracownika {target_name} ({schedule.date} ↔ {target_schedule.date})."
        else:
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
            
    # 2. Notify Employee(s)
    if target_schedule:
        # Direct swap: notify only the target employee
        t_user = session.get(User, target_schedule.user_id)
        if t_user:
            emp_title = "Propozycja wymiany zmiany!"
            emp_body = f"Pracownik {current_user.full_name} proponuje wymianę swojej zmiany na Twoją ({schedule.date} ↔ {target_schedule.date})."
            emp_notif = Notification(
                user_id=t_user.id,
                title=emp_title,
                body=emp_body,
            )
            session.add(emp_notif)
            emp_tokens = push_svc._get_user_tokens(t_user.id)
            if emp_tokens:
                background_tasks.add_task(send_push_to_tokens, emp_tokens, emp_title, emp_body)
    else:
        # Open giveaway: notify all eligible employees with required role
        eligible_employees = session.exec(
            select(User).where(
                User.role_system == RoleSystem.EMPLOYEE,
                User.is_active == True,
                User.id != current_user.id,
                User.tenant_id == current_user.tenant_id
            )
        ).all()
        
        for emp in eligible_employees:
            emp_role_ids = [r.id for r in emp.job_roles] if hasattr(emp, 'job_roles') else []
            if schedule.role_id in emp_role_ids:
                emp_title = "Nowa zmiana do wzięcia!"
                emp_body = f"Pracownik {current_user.full_name} wystawił swoją zmianę na giełdę ({schedule.date})."
                
                emp_notif = Notification(
                    user_id=emp.id,
                    title=emp_title,
                    body=emp_body,
                )
                session.add(emp_notif)
                
                emp_tokens = push_svc._get_user_tokens(emp.id)
                if emp_tokens:
                    background_tasks.add_task(send_push_to_tokens, emp_tokens, emp_title, emp_body)
        
    session.commit()
    session.refresh(giveaway)
    
    return {"id": str(giveaway.id), "status": "created"}

@router.delete("/giveaway/{giveaway_id}")
def cancel_giveaway(
    giveaway_id: UUID,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Cancel a giveaway offer or reject a direct swap proposal"""
    giveaway = session.exec(
        select(ShiftGiveaway)
        .join(User, ShiftGiveaway.offered_by == User.id)
        .where(ShiftGiveaway.id == giveaway_id, User.tenant_id == current_user.tenant_id)
    ).first()
    
    if not giveaway:
        raise HTTPException(status_code=404, detail="Giveaway not found")

    target_schedule = None
    if giveaway.target_shift_id:
        try:
            target_schedule = session.get(Schedule, UUID(str(giveaway.target_shift_id)))
        except ValueError:
            target_schedule = None

    is_offerer = giveaway.offered_by == current_user.id
    is_target_user = target_schedule and target_schedule.user_id == current_user.id

    if not is_offerer and not is_target_user:
        raise HTTPException(status_code=403, detail="Brak uprawnień do anulowania lub odrzucenia tej oferty")
    
    if giveaway.status != GiveawayStatus.OPEN:
        raise HTTPException(status_code=400, detail="Cannot cancel, giveaway already processed")
    
    giveaway.status = GiveawayStatus.CANCELLED
    session.add(giveaway)

    # If rejected by the target employee, notify the offerer
    if is_target_user and not is_offerer:
        offerer = session.get(User, giveaway.offered_by)
        if offerer:
            from ..models import Notification
            from ..services.push_service import PushService, send_push_to_tokens
            push_svc = PushService(session)
            title = "Propozycja wymiany odrzucona"
            body = f"Pracownik {current_user.full_name} odrzucił(a) Twoją propozycję wymiany zmiany."
            notif = Notification(
                user_id=offerer.id,
                title=title,
                body=body,
            )
            session.add(notif)
            tokens = push_svc._get_user_tokens(offerer.id)
            if tokens:
                background_tasks.add_task(send_push_to_tokens, tokens, title, body)

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
            "target_shift_id": str(g.target_shift_id) if g.target_shift_id else None,
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

    from ..models import User
    giveaways = session.exec(
        select(ShiftGiveaway)
        .join(User, ShiftGiveaway.offered_by == User.id)
        .where(
            ShiftGiveaway.status == GiveawayStatus.OPEN,
            ShiftGiveaway.offered_by != current_user.id,
            User.tenant_id == current_user.tenant_id
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

        # Direct swap check (A <-> B)
        target_schedule = None
        target_user = None
        target_shift = None
        if g.target_shift_id:
            try:
                target_uuid = UUID(str(g.target_shift_id))
                target_schedule = session.get(Schedule, target_uuid)
                if target_schedule:
                    target_user = session.get(User, target_schedule.user_id)
                    target_shift = session.get(ShiftDefinition, target_schedule.shift_def_id)
            except ValueError:
                target_schedule = None

            # Direct swap: only visible to the target employee!
            if target_schedule and target_schedule.user_id != current_user.id:
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
                if target_schedule and ms.id == target_schedule.id:
                    # Exclude the shift being exchanged in direct swap
                    continue
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
            "target_shift_id": str(g.target_shift_id) if g.target_shift_id else None,
            "is_direct_swap": bool(g.target_shift_id),
            "target_user_name": target_user.full_name if target_user else None,
            "target_date": target_schedule.date.isoformat() if target_schedule else None,
            "target_shift_name": target_shift.name if target_shift else None,
            "target_start_time": target_shift.start_time.strftime("%H:%M") if target_shift else None,
            "target_end_time": target_shift.end_time.strftime("%H:%M") if target_shift else None,
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
    # Tenant isolation: the giveaway's schedule must belong to the caller's restaurant
    giveaway = session.exec(
        select(ShiftGiveaway)
        .join(Schedule, ShiftGiveaway.schedule_id == Schedule.id)
        .join(User, Schedule.user_id == User.id)
        .where(ShiftGiveaway.id == giveaway_id, User.tenant_id == current_user.tenant_id)
    ).first()
    if not giveaway:
        raise HTTPException(status_code=404, detail="Giveaway not found")
    if giveaway.status != GiveawayStatus.OPEN:
        raise HTTPException(status_code=400, detail="Giveaway is no longer open")
    if giveaway.offered_by == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot claim your own giveaway")

    schedule = giveaway.schedule
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule entry not found")

    # Check if claimant has the required role for the shift
    if schedule.role_id is not None:
        user_role_ids = {r.id for r in current_user.job_roles}
        if schedule.role_id not in user_role_ids:
            raise HTTPException(
                status_code=400,
                detail="Brak wymaganej roli do przejęcia tej zmiany. Wymagana rola musi być przypisana do Twojego profilu."
            )

    target_schedule = None
    if giveaway.target_shift_id:
        try:
            target_uuid = UUID(str(giveaway.target_shift_id))
            target_schedule = session.get(Schedule, target_uuid)
        except ValueError:
            target_schedule = None

        if not target_schedule:
            raise HTTPException(status_code=404, detail="Docelowa zmiana do wymiany nie została znaleziona")

        if target_schedule.user_id != current_user.id:
            raise HTTPException(
                status_code=400,
                detail="Ta oferta wymiany jest skierowana do innego pracownika / innej zmiany."
            )

        offerer = session.get(User, giveaway.offered_by)
        if offerer and target_schedule.role_id is not None:
            offerer_role_ids = {r.id for r in offerer.job_roles}
            if target_schedule.role_id not in offerer_role_ids:
                raise HTTPException(
                    status_code=400,
                    detail="Wystawiający zmianę nie posiada roli wymaganej do Twojej zmiany."
                )

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
            if target_schedule and ms.id == target_schedule.id:
                # Exclude the shift we are giving away in direct swap
                continue
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

    old_user_id = giveaway.offered_by

    # Reassign the schedule to the current user
    schedule.user_id = current_user.id
    session.add(schedule)

    if target_schedule:
        target_schedule.user_id = old_user_id
        session.add(target_schedule)

    # Mark giveaway as taken
    giveaway.status = GiveawayStatus.TAKEN
    giveaway.taken_by = current_user.id
    session.add(giveaway)

    from ..models import ShiftAuditLog
    session.add(
        ShiftAuditLog(
            restaurant_id=current_user.tenant_id,
            shift_id=str(schedule.id),
            changed_by_user_id=current_user.id,
            action="SWAPPED" if target_schedule else "CLAIMED",
            old_value=str(old_user_id),
            new_value=str(current_user.id),
        )
    )
    if target_schedule:
        session.add(
            ShiftAuditLog(
                restaurant_id=current_user.tenant_id,
                shift_id=str(target_schedule.id),
                changed_by_user_id=current_user.id,
                action="SWAPPED",
                old_value=str(current_user.id),
                new_value=str(old_user_id),
            )
        )
    
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
    managers = session.exec(select(User).where(User.role_system == RoleSystem.MANAGER, User.tenant_id == current_user.tenant_id)).all()
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

    # Sync Google Calendars in the background (primitive IDs only, own DB session):
    # remove the event from the previous owner, create it for the new one.
    from ..services.google_calendar_service import reassign_event_task
    background_tasks.add_task(
        reassign_event_task, schedule.id, old_user_id, current_user.id, current_user.tenant_id
    )
    if target_schedule:
        background_tasks.add_task(
            reassign_event_task, target_schedule.id, current_user.id, old_user_id, current_user.tenant_id
        )

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
    managers = session.exec(select(User).where(User.role_system == RoleSystem.MANAGER, User.tenant_id == current_user.tenant_id)).all()
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
    req = session.exec(
        select(LeaveRequest)
        .join(User, LeaveRequest.user_id == User.id)
        .where(LeaveRequest.id == request_id, User.tenant_id == current_user.tenant_id)
    ).first()
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


# ==============================================================================
# MODULE A, B, C: Employee Earnings, Checklists & HACCP, Announcements
# ==============================================================================

from fastapi import Query
from ..services.operations_service import OperationsService
from ..schemas import (
    EmployeeMonthlyEarningsResponse,
    EmployeeChecklistView,
    EmployeeChecklistItemView,
    ChecklistToggleRequest,
    ClockoutValidationResponse,
    HaccpDeviceResponse,
    HaccpLogCreate,
    HaccpLogResponse,
    AnnouncementEmployeeResponse,
)

def get_employee_ops_service(
    session: Session = Depends(get_session),
    tenant_id: int = Depends(require_tenant),
) -> OperationsService:
    return OperationsService(session, tenant_id)


# --- Module A: Employee Monthly Earnings ---

@router.get("/payroll/my", response_model=EmployeeMonthlyEarningsResponse)
def get_my_monthly_earnings(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    ops: OperationsService = Depends(get_employee_ops_service),
    current_user: User = Depends(get_current_user),
):
    return ops.get_employee_monthly_earnings(current_user, year, month)


# --- Module B: Employee Operational Checklists & Digital HACCP ---

@router.get("/checklists", response_model=List[EmployeeChecklistView])
def get_my_daily_checklists(
    target_date: Optional[date] = Query(None),
    ops: OperationsService = Depends(get_employee_ops_service),
    current_user: User = Depends(get_current_user),
):
    d = target_date or date.today()
    return ops.get_employee_checklists(current_user, d)

@router.post("/checklists/items/{item_id}/toggle", response_model=EmployeeChecklistItemView)
def toggle_checklist_item(
    item_id: UUID,
    payload: Optional[ChecklistToggleRequest] = None,
    ops: OperationsService = Depends(get_employee_ops_service),
    current_user: User = Depends(get_current_user),
):
    d = (payload.date if payload and payload.date else None) or date.today()
    is_comp = payload.is_completed if payload else None
    return ops.toggle_checklist_item(current_user, item_id, d, is_completed=is_comp)

@router.get("/checklists/validate-clockout", response_model=ClockoutValidationResponse)
def validate_clockout_checklists(
    target_date: Optional[date] = Query(None),
    ops: OperationsService = Depends(get_employee_ops_service),
    current_user: User = Depends(get_current_user),
):
    d = target_date or date.today()
    return ops.validate_clockout_checklists(current_user, d)

@router.get("/haccp/devices", response_model=List[HaccpDeviceResponse])
def get_employee_haccp_devices(
    ops: OperationsService = Depends(get_employee_ops_service),
    _: User = Depends(get_current_user),
):
    return ops.get_haccp_devices(active_only=True)

@router.get("/haccp/logs", response_model=List[HaccpLogResponse])
def get_employee_haccp_logs(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    violations_only: bool = Query(False),
    ops: OperationsService = Depends(get_employee_ops_service),
    _: User = Depends(get_current_user),
):
    return ops.get_haccp_logs(start_date=start_date, end_date=end_date, violations_only=violations_only)

@router.post("/haccp/logs", response_model=HaccpLogResponse, status_code=201)
def create_employee_haccp_log(
    data: HaccpLogCreate,
    ops: OperationsService = Depends(get_employee_ops_service),
    current_user: User = Depends(get_current_user),
):
    return ops.create_haccp_log(current_user, data)


# --- Module C: Employee Announcements & Read Confirmation ---

@router.get("/announcements", response_model=List[AnnouncementEmployeeResponse])
def get_employee_announcements(
    ops: OperationsService = Depends(get_employee_ops_service),
    current_user: User = Depends(get_current_user),
):
    return ops.get_employee_announcements(current_user)

@router.post("/announcements/{announcement_id}/read")
def mark_announcement_read(
    announcement_id: UUID,
    ops: OperationsService = Depends(get_employee_ops_service),
    current_user: User = Depends(get_current_user),
):
    return ops.mark_announcement_read(current_user, announcement_id)


