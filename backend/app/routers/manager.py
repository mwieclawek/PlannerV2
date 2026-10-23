from typing import List, Optional
from uuid import UUID
from datetime import date, datetime, timedelta
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from sqlmodel import Session, select
from ..database import get_session
from ..models import User, JobRole, ShiftDefinition, StaffingRequirement, RoleSystem, RestaurantConfig, Attendance, AttendanceStatus, Schedule
from ..auth_utils import get_current_user, verify_user_token
from ..schemas import (
    JobRoleCreate, JobRoleResponse, 
    ShiftDefCreate, ShiftDefResponse,
    RequirementCreate, RequirementResponse,
    ConfigUpdate, ConfigResponse,
    UserRolesUpdate, PasswordReset, UserResponse,
    UserUpdate, AttendanceCreate, AttendanceResponse, UserCreate,
    UserStats, DashboardHomeResponse, GiveawayReassignRequest
)
from ..services.manager_service import ManagerService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/manager", tags=["manager"])

# --- Dependencies ---
def get_manager_user(current_user: User = Depends(get_current_user)):
    if current_user.role_system not in (RoleSystem.MANAGER, RoleSystem.ADMIN):
        raise HTTPException(status_code=403, detail="Not a manager")
    return current_user

from ..tenant_context import require_tenant

def get_manager_service(
    session: Session = Depends(get_session),
    tenant_id: int = Depends(require_tenant),
) -> ManagerService:
    return ManagerService(session, tenant_id)

# --- Routes ---

@router.post("/roles", response_model=JobRoleResponse)
def create_role(
    role_in: JobRoleCreate, 
    service: ManagerService = Depends(get_manager_service), 
    _: User = Depends(get_manager_user)
):
    return service.create_role(role_in)

@router.get("/roles", response_model=List[JobRoleResponse])
def get_roles(
    service: ManagerService = Depends(get_manager_service),
    current_user: User = Depends(get_current_user),
):
    roles = service.get_roles()
    if current_user.role_system in (RoleSystem.MANAGER, RoleSystem.ADMIN):
        return roles
    return [
        JobRoleResponse(id=r.id, name=r.name, color_hex=r.color_hex, hourly_rate=None)
        for r in roles
    ]

@router.put("/roles/{role_id}", response_model=JobRoleResponse)
def update_role(
    role_id: int, 
    role_in: JobRoleCreate, 
    service: ManagerService = Depends(get_manager_service), 
    _: User = Depends(get_manager_user)
):
    return service.update_role(role_id, role_in)

@router.delete("/roles/{role_id}")
def delete_role(
    role_id: int, 
    service: ManagerService = Depends(get_manager_service), 
    _: User = Depends(get_manager_user)
):
    service.delete_role(role_id)
    return {"status": "deleted"}

@router.post("/shifts", response_model=ShiftDefResponse)
def create_shift_def(
    shift_in: ShiftDefCreate, 
    service: ManagerService = Depends(get_manager_service), 
    _: User = Depends(get_manager_user)
):
    return service.create_shift(shift_in)

@router.get("/shifts", response_model=List[ShiftDefResponse])
def get_shifts(
    all_shifts: bool = False,
    session: Session = Depends(get_session), 
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(require_tenant),
):
    from ..models import ShiftDefinition, RoleSystem
    shifts = session.exec(select(ShiftDefinition).where(ShiftDefinition.tenant_id == tenant_id)).all()
    
    if all_shifts or current_user.role_system in (RoleSystem.MANAGER, RoleSystem.ADMIN):
        return shifts
        
    user_role_ids = {r.id for r in current_user.job_roles}
    visible_shifts = []
    for s in shifts:
        shift_role_ids = {r.id for r in getattr(s, 'allowed_roles', [])}
        if not shift_role_ids or (shift_role_ids & user_role_ids):
            visible_shifts.append(s)
            
    return visible_shifts

@router.put("/shifts/{shift_id}", response_model=ShiftDefResponse)
def update_shift(
    shift_id: int, 
    shift_in: ShiftDefCreate, 
    background_tasks: BackgroundTasks,
    service: ManagerService = Depends(get_manager_service), 
    current_user: User = Depends(get_manager_user)
):
    return service.update_shift(shift_id, shift_in, background_tasks=background_tasks, changed_by_user_id=current_user.id)

@router.delete("/shifts/{shift_id}")
def delete_shift(
    shift_id: int, 
    service: ManagerService = Depends(get_manager_service), 
    _: User = Depends(get_manager_user)
):
    service.delete_shift(shift_id)
    return {"status": "deleted"}

@router.post("/requirements", response_model=List[RequirementResponse])
def set_requirements(
    reqs: List[RequirementCreate], 
    service: ManagerService = Depends(get_manager_service), 
    _: User = Depends(get_manager_user)
):
    return service.set_requirements(reqs)

@router.get("/requirements", response_model=List[RequirementResponse])
def get_requirements(
    start_date: date, 
    end_date: date, 
    service: ManagerService = Depends(get_manager_service), 
    _: User = Depends(get_manager_user)
):
    return service.get_requirements(start_date, end_date)

@router.put("/users/{user_id}/roles")
def update_user_roles(
    user_id: UUID, 
    update: UserRolesUpdate, 
    service: ManagerService = Depends(get_manager_service), 
    _: User = Depends(get_manager_user)
):
    service.update_user_roles(user_id, update.role_ids)
    return {"status": "updated", "role_ids": update.role_ids}

@router.put("/users/{user_id}/password")
def reset_user_password(
    user_id: UUID, 
    reset: PasswordReset,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_manager_user)
):
    # This involves auth_utils, maybe leave in router or move to UserService? 
    # For now stay here but use schemas.
    from ..auth_utils import get_password_hash
    
    user = session.exec(
        select(User).where(User.id == user_id, User.tenant_id == current_user.tenant_id)
    ).first()
    if not user or user.is_superadmin:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.password_hash = get_password_hash(reset.new_password)
    session.add(user)
    session.commit()
    logger.info(f"[AUTH] Reset hasła użytkownika '{user.username}' (id={user.id}) przez managera '{current_user.username}' [tenant:{current_user.tenant_id}].")
    
    return {"status": "password_reset_success"}

@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID, 
    update: UserUpdate, 
    service: ManagerService = Depends(get_manager_service), 
    _: User = Depends(get_manager_user)
):
    return service.update_user(user_id, update)

@router.get("/users", response_model=List[UserResponse])
def get_users(
    include_inactive: bool = Query(False, description="Include inactive users"),
    service: ManagerService = Depends(get_manager_service), 
    _: User = Depends(get_manager_user)
):
    return service.get_users_with_shifts(include_inactive=include_inactive)

@router.get("/users/{user_id}/stats", response_model=UserStats)
def get_user_stats(
    user_id: UUID, 
    service: ManagerService = Depends(get_manager_service), 
    _: User = Depends(get_manager_user)
):
    return service.get_user_stats(user_id)

@router.get("/dashboard/home", response_model=DashboardHomeResponse)
def get_dashboard_home(
    date: Optional[date] = Query(None, description="Target date for dashboard (default: today)"),
    service: ManagerService = Depends(get_manager_service), 
    _: User = Depends(get_manager_user)
):
    return service.get_dashboard_home(target_date=date)

@router.post("/users", response_model=UserResponse)
def create_user(
    user_in: UserCreate, 
    service: ManagerService = Depends(get_manager_service), 
    _: User = Depends(get_manager_user)
):
    return service.create_user(user_in)

@router.get("/config", response_model=ConfigResponse)
def get_config(service: ManagerService = Depends(get_manager_service), _: User = Depends(get_current_user)):
    return service.get_config()

@router.post("/config", response_model=ConfigResponse)
def update_config(
    update: ConfigUpdate, 
    service: ManagerService = Depends(get_manager_service), 
    _: User = Depends(get_manager_user)
):
    return service.update_config(update)

@router.get("/availability")
def get_team_availability(
    week_start: date,
    week_end: date,
    session: Session = Depends(get_session),
    _: User = Depends(get_manager_user),
    tenant_id: int = Depends(require_tenant),
):
    """Zwraca dostępność wszystkich pracowników w danym tygodniu"""
    from ..models import Availability
    availabilities = session.exec(
        select(Availability)
        .where(Availability.date >= week_start)
        .where(Availability.date <= week_end)
        .join(User, Availability.user_id == User.id)
        .where(User.tenant_id == tenant_id)
    ).all()
    
    # Group by user
    result = {}
    for av in availabilities:
        user_id = str(av.user_id)
        if user_id not in result:
            result[user_id] = {
                "user_id": user_id,
                "user_name": av.user.full_name,
                "entries": []
            }
        result[user_id]["entries"].append({
            "date": av.date.isoformat(),
            "shift_def_id": av.shift_def_id,
            "status": av.status.value
        })
    
    return list(result.values())

@router.get("/schedules/available-employees")
def get_available_employees(
    date: date,
    shift_def_id: int,
    service: ManagerService = Depends(get_manager_service),
    _: User = Depends(get_manager_user)
):
    """Get list of employees and their availability status for a specific shift instance"""
    return service.get_available_employees_for_shift(date, shift_def_id)

# Attendance Management Endpoints
from ..models import Attendance, AttendanceStatus


def _get_tenant_attendance(session: Session, attendance_id: UUID, current_user: User):
    """Fetch an attendance record only if its employee belongs to the caller's restaurant."""
    return session.exec(
        select(Attendance)
        .join(User, Attendance.user_id == User.id)
        .where(Attendance.id == attendance_id, User.tenant_id == current_user.tenant_id)
    ).first()

@router.get("/attendance/pending")
def get_pending_attendance(
    session: Session = Depends(get_session),
    _: User = Depends(get_manager_user),
    tenant_id: int = Depends(require_tenant),
):
    """Get all attendance records pending manager approval"""
    attendances = session.exec(
        select(Attendance)
        .where(Attendance.status == AttendanceStatus.PENDING)
        .join(User, Attendance.user_id == User.id)
        .where(User.tenant_id == tenant_id)
    ).all()
    
    return [{
        "id": str(a.id),
        "user_id": str(a.user_id),
        "user_name": a.user.full_name,
        "date": a.date.isoformat(),
        "check_in": a.check_in.strftime("%H:%M"),
        "check_out": a.check_out.strftime("%H:%M"),
        "was_scheduled": a.was_scheduled,
        "status": a.status.value,
        "checklist_skip_reason": a.checklist_skip_reason,
        "is_absent": bool(a.is_absent),
        "absence_reason": a.absence_reason,
    } for a in attendances]

@router.put("/attendance/{attendance_id}/confirm")
def confirm_attendance(
    attendance_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_manager_user)
):
    """Manager confirms unscheduled attendance"""
    attendance = _get_tenant_attendance(session, attendance_id, current_user)
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance not found")
    
    old_status = attendance.status.value
    attendance.status = AttendanceStatus.CONFIRMED
    session.add(attendance)
    from ..models import ShiftAuditLog
    session.add(ShiftAuditLog(
        restaurant_id=current_user.tenant_id,
        shift_id=str(attendance.schedule_id or attendance.id),
        changed_by_user_id=current_user.id,
        action="CONFIRM_ATTENDANCE",
        old_value=old_status,
        new_value=AttendanceStatus.CONFIRMED.value
    ))
    session.commit()
    logger.info(
        f"[ATTENDANCE] Manager '{current_user.username}' zatwierdził nieplanowaną obecność {attendance.id} "
        f"(użytkownik {attendance.user_id}, data {attendance.date}) [tenant:{current_user.tenant_id}]."
    )
    return {"status": "confirmed"}

@router.put("/attendance/{attendance_id}/reject")
def reject_attendance(
    attendance_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_manager_user)
):
    """Manager rejects unscheduled attendance"""
    attendance = _get_tenant_attendance(session, attendance_id, current_user)
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance not found")
    
    old_status = attendance.status.value
    attendance.status = AttendanceStatus.REJECTED
    session.add(attendance)
    from ..models import ShiftAuditLog
    session.add(ShiftAuditLog(
        restaurant_id=current_user.tenant_id,
        shift_id=str(attendance.schedule_id or attendance.id),
        changed_by_user_id=current_user.id,
        action="REJECT_ATTENDANCE",
        old_value=old_status,
        new_value=AttendanceStatus.REJECTED.value
    ))
    session.commit()
    logger.info(
        f"[ATTENDANCE] Manager '{current_user.username}' odrzucił nieplanowaną obecność {attendance.id} "
        f"(użytkownik {attendance.user_id}, data {attendance.date}) [tenant:{current_user.tenant_id}]."
    )
    return {"status": "rejected"}

@router.get("/attendance/export")
async def export_attendance_pdf(
    start_date: date,
    end_date: date,
    status: Optional[str] = Query(None, description="Filter by status: PENDING, CONFIRMED, REJECTED"),
    token: Optional[str] = Query(None),
    session: Session = Depends(get_session)
):
    """Export attendance list to PDF"""
    # Verify auth via token query param
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = await verify_user_token(token, session)
    # Check if user is manager (using RoleSystem enum from models)
    if user.role_system != RoleSystem.MANAGER:
        raise HTTPException(status_code=403, detail="Not authorized")

    query = select(Attendance).where(
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).join(User, Attendance.user_id == User.id).where(User.tenant_id == user.tenant_id)
    
    if status:
        try:
            status_enum = AttendanceStatus(status.upper())
            query = query.where(Attendance.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
            
    attendances = session.exec(query).all()
    
    # Calculate hours
    hours_map = {}
    for att in attendances:
        if att.status == AttendanceStatus.CONFIRMED and not getattr(att, "is_absent", False):
            start_dt = datetime.combine(att.date, att.check_in)
            end_dt = datetime.combine(att.date, att.check_out)
            if end_dt <= start_dt:
                 end_dt += timedelta(days=1)
            duration = (end_dt - start_dt).total_seconds() / 3600
            
            user_name = att.user.full_name
            hours_map[user_name] = hours_map.get(user_name, 0) + duration

    # Generate PDF
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    
    # Title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, f"Attendance List: {start_date} - {end_date}")
    y -= 30
    
    # Filters
    p.setFont("Helvetica", 10)
    if status:
        p.drawString(50, y, f"Filter Status: {status}")
        y -= 20
        
    # Table Header
    y -= 20
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Employee")
    p.drawString(200, y, "Date")
    p.drawString(300, y, "Time")
    p.drawString(400, y, "Status")
    p.line(50, y-5, 500, y-5)
    y -= 20
    
    # Data
    p.setFont("Helvetica", 10)
    for att in attendances:
        if y < 50:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica-Bold", 10) # Re-print header? Simplified: just continue
            p.drawString(50, y, "Employee")
            p.drawString(200, y, "Date")
            p.drawString(300, y, "Time")
            p.drawString(400, y, "Status")
            y -= 20
            p.setFont("Helvetica", 10)
            
        p.drawString(50, y, att.user.full_name)
        p.drawString(200, y, str(att.date))
        if getattr(att, "is_absent", False):
            p.drawString(300, y, "NIEOBECNY")
        else:
            p.drawString(300, y, f"{att.check_in.strftime('%H:%M')} - {att.check_out.strftime('%H:%M')}")
        p.drawString(400, y, att.status.value)
        y -= 15
        
    # Summary Table
    if y < 100:
        p.showPage()
        y = height - 50
    
    y -= 30
    p.line(50, y+10, 500, y+10) # Separator
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Hours Summary")
    y -= 20
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Employee")
    p.drawString(200, y, "Total Hours")
    y -= 20
    p.setFont("Helvetica", 10)
    
    for name, hours in hours_map.items():
        if y < 50:
             p.showPage()
             y = height - 50
             p.setFont("Helvetica-Bold", 10)
             p.drawString(50, y, "Employee")
             p.drawString(200, y, "Total Hours")
             y -= 20
             p.setFont("Helvetica", 10)

        p.drawString(50, y, name)
        p.drawString(200, y, f"{hours:.1f}")
        y -= 15

    p.save()
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=attendance_export.pdf"}
    )

@router.get("/attendance")
def get_all_attendance(
    start_date: date,
    end_date: date,
    status: Optional[str] = Query(None, description="Filter by status: PENDING, CONFIRMED, REJECTED"),
    session: Session = Depends(get_session),
    _: User = Depends(get_manager_user),
    tenant_id: int = Depends(require_tenant),
):
    """Get all attendance records within date range, optionally filtered by status"""
    query = select(Attendance).where(
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).join(User, Attendance.user_id == User.id).where(User.tenant_id == tenant_id)
    
    if status:
        try:
            status_enum = AttendanceStatus(status.upper())
            query = query.where(Attendance.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}. Must be PENDING, CONFIRMED, or REJECTED.")
    
    attendances = session.exec(query).all()
    
    return [{
        "id": str(a.id),
        "user_id": str(a.user_id),
        "user_name": a.user.full_name,
        "date": a.date.isoformat(),
        "check_in": a.check_in.strftime("%H:%M"),
        "check_out": a.check_out.strftime("%H:%M"),
        "was_scheduled": a.was_scheduled,
        "status": a.status.value,
        "checklist_skip_reason": a.checklist_skip_reason,
        "is_absent": bool(a.is_absent),
        "absence_reason": a.absence_reason,
    } for a in attendances]

@router.post("/attendance", response_model=AttendanceResponse)
def create_attendance(
    attendance_in: AttendanceCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_manager_user)
):
    """Manually register attendance for an employee"""
    employee = session.exec(
        select(User).where(User.id == attendance_in.user_id, User.tenant_id == current_user.tenant_id)
    ).first()
    if not employee:
        raise HTTPException(status_code=404, detail="User not found")
    if attendance_in.schedule_id:
        sched = session.exec(
            select(Schedule).join(User, Schedule.user_id == User.id)
            .where(Schedule.id == attendance_in.schedule_id, User.tenant_id == current_user.tenant_id)
        ).first()
        if not sched:
            raise HTTPException(status_code=404, detail="Schedule not found")
    attendance = Attendance(**attendance_in.dict())
    session.add(attendance)
    session.commit()
    session.refresh(attendance)
    
    logger.info(
        f"[ATTENDANCE] Manager '{current_user.username}' ręcznie zarejestrował obecność (id={attendance.id}): "
        f"pracownik '{employee.username}' (id={employee.id}), data={attendance.date}, "
        f"godziny={attendance.check_in}-{attendance.check_out}, status={attendance.status.value} [tenant:{current_user.tenant_id}]."
    )

    # Ensure user relation is loaded
    response_data = AttendanceResponse.from_orm(attendance)
    if attendance.user:
        response_data.user_name = attendance.user.full_name
    return response_data

@router.get("/employee-hours")
def get_employee_hours(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000, le=2100),
    session: Session = Depends(get_session),
    _: User = Depends(get_manager_user),
    tenant_id: int = Depends(require_tenant),
):
    """Get monthly hours summary for all employees with availability info"""
    from ..models import Schedule, Availability
    from calendar import monthrange
    
    # Calculate month date range
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])
    
    # Get all schedules for the month
    schedules = session.exec(
        select(Schedule).where(
            Schedule.date >= first_day,
            Schedule.date <= last_day
        ).join(User, Schedule.user_id == User.id).where(User.tenant_id == tenant_id)
    ).all()
    
    # Get shift definitions for time calculations
    all_shifts = session.exec(select(ShiftDefinition).where(ShiftDefinition.tenant_id == tenant_id)).all()
    shift_map = {s.id: s for s in all_shifts}
    
    # Get all employees
    employees = session.exec(
        select(User).where(User.role_system == RoleSystem.EMPLOYEE, User.tenant_id == tenant_id)
    ).all()
    
    # Get availability for the month (to know who submitted)
    availabilities = session.exec(
        select(Availability).where(
            Availability.date >= first_day,
            Availability.date <= last_day
        ).join(User, Availability.user_id == User.id).where(User.tenant_id == tenant_id)
    ).all()
    users_with_availability = {str(a.user_id) for a in availabilities}
    
    # Calculate hours per employee
    hours_by_user = {}
    for schedule in schedules:
        uid = str(schedule.user_id)
        shift = shift_map.get(schedule.shift_def_id)
        if not shift:
            continue
        
        # Calculate shift duration in hours
        start_dt = datetime.combine(date.today(), shift.start_time)
        end_dt = datetime.combine(date.today(), shift.end_time)
        if end_dt <= start_dt:
            # Overnight shift
            end_dt += timedelta(days=1)
        duration_hours = (end_dt - start_dt).total_seconds() / 3600
        
        if uid not in hours_by_user:
            hours_by_user[uid] = {"total_hours": 0.0, "shift_count": 0}
        hours_by_user[uid]["total_hours"] += duration_hours
        hours_by_user[uid]["shift_count"] += 1
    
    # Build result for all employees
    result = []
    for emp in employees:
        uid = str(emp.id)
        data = hours_by_user.get(uid, {"total_hours": 0.0, "shift_count": 0})
        result.append({
            "user_id": uid,
            "user_name": emp.full_name,
            "total_hours": round(data["total_hours"], 1),
            "shift_count": data["shift_count"],
            "has_availability": uid in users_with_availability
        })
    
    # Sort by total_hours descending
    result.sort(key=lambda x: x["total_hours"], reverse=True)
    
    return result


# --- Shift Giveaway endpoints ---

@router.get("/giveaways")
def get_giveaways(
    service: ManagerService = Depends(get_manager_service),
    _: User = Depends(get_manager_user)
):
    """Get all open shift giveaways with replacement suggestions"""
    return service.get_open_giveaways()

@router.post("/giveaways/{giveaway_id}/reassign")
def reassign_giveaway(
    giveaway_id: UUID,
    request: GiveawayReassignRequest,
    background_tasks: BackgroundTasks,
    service: ManagerService = Depends(get_manager_service),
    current_user: User = Depends(get_manager_user)
):
    """Reassign a giveaway shift to a new user or execute direct swap"""
    return service.reassign_giveaway(
        giveaway_id,
        request.new_user_id,
        target_shift_id=request.target_shift_id,
        background_tasks=background_tasks,
        changed_by_user_id=current_user.id
    )

@router.post("/giveaways/{giveaway_id}/swap")
def swap_giveaway(
    giveaway_id: UUID,
    request: GiveawayReassignRequest,
    background_tasks: BackgroundTasks,
    service: ManagerService = Depends(get_manager_service),
    current_user: User = Depends(get_manager_user)
):
    """Execute direct shift swap (A <-> B)"""
    return service.reassign_giveaway(
        giveaway_id,
        request.new_user_id,
        target_shift_id=request.target_shift_id,
        background_tasks=background_tasks,
        changed_by_user_id=current_user.id
    )

@router.delete("/giveaways/{giveaway_id}")
def cancel_giveaway(
    giveaway_id: UUID,
    service: ManagerService = Depends(get_manager_service),
    _: User = Depends(get_manager_user)
):
    """Cancel a giveaway (manager action)"""
    service.cancel_giveaway(giveaway_id)
    return {"status": "cancelled"}

# --- Leave Requests endpoints ---

from ..schemas import LeaveRequestResponse

@router.get("/leave-requests", response_model=List[LeaveRequestResponse])
def get_all_leave_requests(
    status: Optional[str] = None,
    service: ManagerService = Depends(get_manager_service),
    _: User = Depends(get_manager_user)
):
    """List all leave requests"""
    requests = service.get_all_leave_requests(status)
    return [
        LeaveRequestResponse(
            id=item["req"].id,
            user_id=item["req"].user_id,
            user_name=item["user"].full_name,
            start_date=item["req"].start_date,
            end_date=item["req"].end_date,
            reason=item["req"].reason,
            status=str(item["req"].status.value),
            created_at=item["req"].created_at,
            reviewed_at=item["req"].reviewed_at,
        ) for item in requests
    ]

@router.post("/leave-requests/{request_id}/approve")
def approve_leave_request(
    request_id: UUID,
    background_tasks: BackgroundTasks,
    service: ManagerService = Depends(get_manager_service),
    current_user: User = Depends(get_manager_user)
):
    """Approve a PENDING request"""
    service.process_leave_request(request_id, approved=True, manager_id=current_user.id, background_tasks=background_tasks)
    return {"status": "approved"}

@router.post("/leave-requests/{request_id}/reject")
def reject_leave_request(
    request_id: UUID,
    background_tasks: BackgroundTasks,
    service: ManagerService = Depends(get_manager_service),
    current_user: User = Depends(get_manager_user)
):
    """Reject a PENDING request"""
    service.process_leave_request(request_id, approved=False, manager_id=current_user.id, background_tasks=background_tasks)
    return {"status": "rejected"}

@router.get("/leave-requests/calendar")
def get_leave_calendar(
    year: int,
    month: int,
    service: ManagerService = Depends(get_manager_service),
    _: User = Depends(get_manager_user)
):
    """Returns calendar entries for leave requests"""
    return service.get_leave_calendar(year, month)

# --- Schedule Publishing & Audit Log ---
from ..schemas import PublishScheduleRequest, ShiftAuditLogResponse
from ..models import ShiftAuditLog

@router.post("/schedules/publish")
def publish_schedules(
    background_tasks: BackgroundTasks,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    payload: Optional[PublishScheduleRequest] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_manager_user)
):
    """Publish schedules in date range (marks is_published=True, sends push, syncs Google Calendar)"""
    s_date = (payload.start_date if payload and payload.start_date else None) or start_date
    e_date = (payload.end_date if payload and payload.end_date else None) or end_date
    if not s_date or not e_date:
        raise HTTPException(status_code=400, detail="start_date and end_date are required")

    from ..services.scheduler_service import SchedulerService
    sched_service = SchedulerService(session, current_user.tenant_id)
    count = sched_service.publish_schedule(s_date, e_date, background_tasks, changed_by_user_id=current_user.id)
    return {"status": "published", "count": count}

@router.get("/shifts/{shift_id}/audit-log", response_model=List[ShiftAuditLogResponse])
def get_shift_audit_log(
    shift_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_manager_user)
):
    """Get audit log for a shift or schedule (tenant-filtered)"""
    logs = session.exec(
        select(ShiftAuditLog)
        .where(
            ShiftAuditLog.restaurant_id == current_user.tenant_id,
            ShiftAuditLog.shift_id == str(shift_id)
        )
        .order_by(ShiftAuditLog.created_at.desc())
    ).all()

    res = []
    for l in logs:
        u_name = None
        if l.changed_by_user_id:
            u = session.get(User, l.changed_by_user_id)
            if u:
                u_name = u.full_name
        res.append(
            ShiftAuditLogResponse(
                id=l.id,
                restaurant_id=l.restaurant_id,
                shift_id=l.shift_id,
                changed_by_user_id=l.changed_by_user_id,
                changed_by_user_name=u_name,
                action=l.action,
                old_value=l.old_value,
                new_value=l.new_value,
                created_at=l.created_at
            )
        )
    return res


# ==============================================================================
# MODULE A, B, C: Payroll / Closeout, Checklists & HACCP, Announcements
# ==============================================================================

from fastapi import Request
from ..services.operations_service import OperationsService
from ..tenant_context import set_current_tenant_id
from ..schemas import (
    DailyCloseoutCreate,
    DailyCloseoutSummaryResponse,
    MonthlyPayrollResponse,
    ChecklistTemplateCreate,
    ChecklistTemplateResponse,
    EmployeeChecklistView,
    HaccpDeviceCreate,
    HaccpDeviceResponse,
    HaccpLogCreate,
    HaccpLogResponse,
    AnnouncementCreate,
    AnnouncementManagerResponse,
)

def get_operations_service(
    session: Session = Depends(get_session),
    tenant_id: int = Depends(require_tenant),
) -> OperationsService:
    return OperationsService(session, tenant_id)

async def _resolve_export_manager(
    request: Request,
    token: Optional[str],
    session: Session,
) -> User:
    """Resolve manager user from either ?token= query param or Authorization: Bearer header."""
    resolved_token = token
    if not resolved_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            resolved_token = auth_header.split(" ", 1)[1].strip()
    if not resolved_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await verify_user_token( resolved_token, session)
    if user.role_system not in (RoleSystem.MANAGER, RoleSystem.ADMIN):
        raise HTTPException(status_code=403, detail="Not authorized")
    if user.tenant_id is not None:
        set_current_tenant_id(user.tenant_id)
    return user


# --- Module A: Daily Closeout & Payroll ---

@router.post("/closeouts", response_model=DailyCloseoutSummaryResponse)
def upsert_daily_closeout(
    data: DailyCloseoutCreate,
    ops: OperationsService = Depends(get_operations_service),
    current_user: User = Depends(get_manager_user),
):
    return ops.upsert_daily_closeout(data, current_user.id)

@router.get("/closeouts", response_model=List[DailyCloseoutSummaryResponse])
def get_closeouts_range(
    start_date: date,
    end_date: date,
    ops: OperationsService = Depends(get_operations_service),
    _: User = Depends(get_manager_user),
):
    return ops.get_closeouts_range(start_date, end_date)

@router.get("/closeouts/{target_date}", response_model=DailyCloseoutSummaryResponse)
def get_daily_closeout_summary(
    target_date: date,
    ops: OperationsService = Depends(get_operations_service),
    _: User = Depends(get_manager_user),
):
    return ops.get_daily_closeout_summary(target_date)

@router.get("/payroll", response_model=MonthlyPayrollResponse)
def get_monthly_payroll(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    ops: OperationsService = Depends(get_operations_service),
    _: User = Depends(get_manager_user),
):
    return ops.get_monthly_payroll(year, month)

@router.get("/payroll/export/csv")
async def export_monthly_payroll_csv(
    request: Request,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    token: Optional[str] = Query(None),
    session: Session = Depends(get_session),
):
    user = await _resolve_export_manager(request, token, session)
    ops = OperationsService(session, user.tenant_id)
    csv_buf = ops.export_monthly_payroll_csv(year, month)
    return StreamingResponse(
        csv_buf,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=payroll_{year}_{month:02d}.csv"},
    )

@router.get("/payroll/export/pdf")
async def export_monthly_payroll_pdf(
    request: Request,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    token: Optional[str] = Query(None),
    session: Session = Depends(get_session),
):
    user = await _resolve_export_manager(request, token, session)
    ops = OperationsService(session, user.tenant_id)
    pdf_buf = ops.export_monthly_payroll_pdf(year, month)
    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=payroll_{year}_{month:02d}.pdf"},
    )


# --- Module B: Operational Checklists & Digital HACCP ---

@router.get("/checklists", response_model=List[ChecklistTemplateResponse])
def get_checklist_templates(
    include_inactive: bool = Query(False),
    ops: OperationsService = Depends(get_operations_service),
    _: User = Depends(get_manager_user),
):
    return ops.get_checklist_templates(include_inactive=include_inactive)

@router.post("/checklists", response_model=ChecklistTemplateResponse, status_code=201)
def create_checklist_template(
    data: ChecklistTemplateCreate,
    ops: OperationsService = Depends(get_operations_service),
    _: User = Depends(get_manager_user),
):
    return ops.create_checklist_template(data)

@router.put("/checklists/{template_id}", response_model=ChecklistTemplateResponse)
def update_checklist_template(
    template_id: UUID,
    data: ChecklistTemplateCreate,
    ops: OperationsService = Depends(get_operations_service),
    _: User = Depends(get_manager_user),
):
    return ops.update_checklist_template(template_id, data)

@router.delete("/checklists/{template_id}")
def delete_checklist_template(
    template_id: UUID,
    ops: OperationsService = Depends(get_operations_service),
    _: User = Depends(get_manager_user),
):
    ops.delete_checklist_template(template_id)
    return {"status": "deleted"}

@router.get("/checklists/daily/{target_date}", response_model=List[EmployeeChecklistView])
def get_manager_daily_checklists(
    target_date: date,
    ops: OperationsService = Depends(get_operations_service),
    current_user: User = Depends(get_manager_user),
):
    return ops.get_employee_checklists(current_user, target_date)

@router.get("/haccp/devices", response_model=List[HaccpDeviceResponse])
def get_haccp_devices(
    include_inactive: bool = Query(False),
    ops: OperationsService = Depends(get_operations_service),
    _: User = Depends(get_manager_user),
):
    return ops.get_haccp_devices(active_only=not include_inactive)

@router.post("/haccp/devices", response_model=HaccpDeviceResponse, status_code=201)
def create_haccp_device(
    data: HaccpDeviceCreate,
    ops: OperationsService = Depends(get_operations_service),
    _: User = Depends(get_manager_user),
):
    return ops.create_haccp_device(data)

@router.delete("/haccp/devices/{device_id}")
def delete_haccp_device(
    device_id: UUID,
    ops: OperationsService = Depends(get_operations_service),
    _: User = Depends(get_manager_user),
):
    ops.delete_haccp_device(device_id)
    return {"status": "deleted"}

@router.get("/haccp/logs", response_model=List[HaccpLogResponse])
def get_haccp_logs(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    violations_only: bool = Query(False),
    ops: OperationsService = Depends(get_operations_service),
    _: User = Depends(get_manager_user),
):
    return ops.get_haccp_logs(start_date=start_date, end_date=end_date, violations_only=violations_only)

@router.post("/haccp/logs", response_model=HaccpLogResponse, status_code=201)
def create_manager_haccp_log(
    data: HaccpLogCreate,
    ops: OperationsService = Depends(get_operations_service),
    current_user: User = Depends(get_manager_user),
):
    return ops.create_haccp_log(current_user, data)

@router.get("/haccp/export/pdf")
async def export_haccp_pdf(
    request: Request,
    start_date: date,
    end_date: date,
    token: Optional[str] = Query(None),
    session: Session = Depends(get_session),
):
    user = await _resolve_export_manager(request, token, session)
    ops = OperationsService(session, user.tenant_id)
    pdf_buf = ops.export_haccp_pdf(start_date, end_date)
    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=haccp_sanepid_{start_date}_{end_date}.pdf"},
    )


# --- Module C: Announcements & Read Receipts ---

@router.get("/announcements", response_model=List[AnnouncementManagerResponse])
def get_manager_announcements(
    ops: OperationsService = Depends(get_operations_service),
    _: User = Depends(get_manager_user),
):
    return ops.get_manager_announcements()

@router.post("/announcements", response_model=AnnouncementManagerResponse, status_code=201)
def create_announcement(
    data: AnnouncementCreate,
    background_tasks: BackgroundTasks,
    ops: OperationsService = Depends(get_operations_service),
    current_user: User = Depends(get_manager_user),
):
    return ops.create_announcement(current_user, data, background_tasks=background_tasks)

@router.get("/announcements/{announcement_id}/receipts", response_model=AnnouncementManagerResponse)
def get_announcement_receipts(
    announcement_id: UUID,
    ops: OperationsService = Depends(get_operations_service),
    _: User = Depends(get_manager_user),
):
    return ops.get_announcement_receipts(announcement_id)

@router.delete("/announcements/{announcement_id}")
def delete_announcement(
    announcement_id: UUID,
    ops: OperationsService = Depends(get_operations_service),
    _: User = Depends(get_manager_user),
):
    ops.delete_announcement(announcement_id)
    return {"status": "deleted"}


