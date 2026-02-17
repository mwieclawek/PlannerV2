from typing import List, Optional
from uuid import UUID
from datetime import date, datetime, timedelta
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from sqlmodel import Session, select
from ..database import get_session
from ..models import User, JobRole, ShiftDefinition, StaffingRequirement, RoleSystem, RestaurantConfig, Attendance, AttendanceStatus
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

router = APIRouter(prefix="/manager", tags=["manager"])

# --- Dependencies ---
def get_manager_user(current_user: User = Depends(get_current_user)):
    if current_user.role_system != RoleSystem.MANAGER:
        raise HTTPException(status_code=403, detail="Not a manager")
    return current_user

def get_manager_service(session: Session = Depends(get_session)) -> ManagerService:
    return ManagerService(session)

# --- Routes ---

@router.post("/roles", response_model=JobRoleResponse)
def create_role(
    role_in: JobRoleCreate, 
    service: ManagerService = Depends(get_manager_service), 
    _: User = Depends(get_manager_user)
):
    return service.create_role(role_in)

@router.get("/roles", response_model=List[JobRoleResponse])
def get_roles(service: ManagerService = Depends(get_manager_service), _: User = Depends(get_current_user)):
    return service.get_roles()

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
def get_shifts(session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    # Simple list doesnt necessarily need service but for consistency:
    return session.exec(select(ShiftDefinition)).all()

@router.put("/shifts/{shift_id}", response_model=ShiftDefResponse)
def update_shift(
    shift_id: int, 
    shift_in: ShiftDefCreate, 
    service: ManagerService = Depends(get_manager_service), 
    _: User = Depends(get_manager_user)
):
    return service.update_shift(shift_id, shift_in)

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
    _: User = Depends(get_manager_user)
):
    # This involves auth_utils, maybe leave in router or move to UserService? 
    # For now stay here but use schemas.
    from ..auth_utils import get_password_hash
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.password_hash = get_password_hash(reset.new_password)
    session.add(user)
    session.commit()
    
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
    _: User = Depends(get_manager_user)
):
    """Zwraca dostępność wszystkich pracowników w danym tygodniu"""
    from ..models import Availability
    availabilities = session.exec(
        select(Availability)
        .where(Availability.date >= week_start)
        .where(Availability.date <= week_end)
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

# Attendance Management Endpoints
from ..models import Attendance, AttendanceStatus

@router.get("/attendance/pending")
def get_pending_attendance(
    session: Session = Depends(get_session),
    _: User = Depends(get_manager_user)
):
    """Get all attendance records pending manager approval"""
    attendances = session.exec(
        select(Attendance).where(Attendance.status == AttendanceStatus.PENDING)
    ).all()
    
    return [{
        "id": str(a.id),
        "user_id": str(a.user_id),
        "user_name": a.user.full_name,
        "date": a.date.isoformat(),
        "check_in": a.check_in.strftime("%H:%M"),
        "check_out": a.check_out.strftime("%H:%M"),
        "was_scheduled": a.was_scheduled,
        "status": a.status.value
    } for a in attendances]

@router.put("/attendance/{attendance_id}/confirm")
def confirm_attendance(
    attendance_id: str,
    session: Session = Depends(get_session),
    _: User = Depends(get_manager_user)
):
    """Manager confirms unscheduled attendance"""
    from uuid import UUID
    attendance = session.get(Attendance, UUID(attendance_id))
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance not found")
    
    attendance.status = AttendanceStatus.CONFIRMED
    session.add(attendance)
    session.commit()
    return {"status": "confirmed"}

@router.put("/attendance/{attendance_id}/reject")
def reject_attendance(
    attendance_id: str,
    session: Session = Depends(get_session),
    _: User = Depends(get_manager_user)
):
    """Manager rejects unscheduled attendance"""
    from uuid import UUID
    attendance = session.get(Attendance, UUID(attendance_id))
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance not found")
    
    attendance.status = AttendanceStatus.REJECTED
    session.add(attendance)
    session.commit()
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
    )
    
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
        if att.status == AttendanceStatus.CONFIRMED:
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
    _: User = Depends(get_manager_user)
):
    """Get all attendance records within date range, optionally filtered by status"""
    query = select(Attendance).where(
        Attendance.date >= start_date,
        Attendance.date <= end_date
    )
    
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
        "status": a.status.value
    } for a in attendances]

@router.post("/attendance", response_model=AttendanceResponse)
def create_attendance(
    attendance_in: AttendanceCreate,
    session: Session = Depends(get_session),
    _: User = Depends(get_manager_user)
):
    """Manually register attendance for an employee"""
    attendance = Attendance(**attendance_in.dict())
    session.add(attendance)
    session.commit()
    session.refresh(attendance)
    
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
    _: User = Depends(get_manager_user)
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
        )
    ).all()
    
    # Get shift definitions for time calculations
    all_shifts = session.exec(select(ShiftDefinition)).all()
    shift_map = {s.id: s for s in all_shifts}
    
    # Get all employees
    employees = session.exec(
        select(User).where(User.role_system == RoleSystem.EMPLOYEE)
    ).all()
    
    # Get availability for the month (to know who submitted)
    availabilities = session.exec(
        select(Availability).where(
            Availability.date >= first_day,
            Availability.date <= last_day
        )
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
    service: ManagerService = Depends(get_manager_service),
    _: User = Depends(get_manager_user)
):
    """Reassign a giveaway shift to a new user"""
    return service.reassign_giveaway(giveaway_id, request.new_user_id)

@router.delete("/giveaways/{giveaway_id}")
def cancel_giveaway(
    giveaway_id: UUID,
    service: ManagerService = Depends(get_manager_service),
    _: User = Depends(get_manager_user)
):
    """Cancel a giveaway (manager action)"""
    service.cancel_giveaway(giveaway_id)
    return {"status": "cancelled"}
