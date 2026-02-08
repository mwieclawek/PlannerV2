from typing import List
from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ..database import get_session
from ..models import User, JobRole, ShiftDefinition, StaffingRequirement, RoleSystem, RestaurantConfig
from ..auth_utils import get_current_user
from ..schemas import (
    JobRoleCreate, JobRoleResponse, 
    ShiftDefCreate, ShiftDefResponse,
    RequirementCreate, RequirementResponse,
    ConfigUpdate, ConfigResponse,
    UserRolesUpdate, PasswordReset, UserResponse
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

@router.get("/users", response_model=List[UserResponse])
def get_users(session: Session = Depends(get_session), _: User = Depends(get_manager_user)):
    users = session.exec(select(User)).all()
    # SQLModel automatically handles the conversion to response_model
    # including relationship mapping if configured
    result = []
    for u in users:
        result.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "role_system": u.role_system,
            "created_at": u.created_at,
            "job_roles": [r.id for r in u.job_roles]
        })
    return result

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

