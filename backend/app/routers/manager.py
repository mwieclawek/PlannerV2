from typing import List
from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ..database import get_session
from ..models import User, JobRole, ShiftDefinition, StaffingRequirement, RoleSystem
from ..auth_utils import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/manager", tags=["manager"])

# --- Pydantic Models for Input ---
class JobRoleCreate(BaseModel):
    name: str
    color_hex: str

class ShiftDefCreate(BaseModel):
    name: str
    start_time: str # HH:MM
    end_time: str   # HH:MM

class RequirementCreate(BaseModel):
    date: date
    shift_def_id: int
    role_id: int
    min_count: int

# --- Dependencies ---
def get_manager_user(current_user: User = Depends(get_current_user)):
    if current_user.role_system != RoleSystem.MANAGER:
        raise HTTPException(status_code=403, detail="Not a manager")
    return current_user

# --- Routes ---

@router.post("/roles", response_model=JobRole)
def create_role(role_in: JobRoleCreate, session: Session = Depends(get_session), _: User = Depends(get_manager_user)):
    role = JobRole(name=role_in.name, color_hex=role_in.color_hex)
    session.add(role)
    session.commit()
    session.refresh(role)
    return role

@router.get("/roles", response_model=List[JobRole])
def get_roles(session: Session = Depends(get_session), _: User = Depends(get_current_user)): # Employees need to see roles too
    return session.exec(select(JobRole)).all()

@router.post("/shifts", response_model=ShiftDefinition)
def create_shift_def(shift_in: ShiftDefCreate, session: Session = Depends(get_session), _: User = Depends(get_manager_user)):
    # Simple parse for now
    from datetime import datetime
    s_time = datetime.strptime(shift_in.start_time, "%H:%M").time()
    e_time = datetime.strptime(shift_in.end_time, "%H:%M").time()
    
    shift = ShiftDefinition(name=shift_in.name, start_time=s_time, end_time=e_time)
    session.add(shift)
    session.commit()
    session.refresh(shift)
    return shift

@router.get("/shifts", response_model=List[ShiftDefinition])
def get_shifts(session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    return session.exec(select(ShiftDefinition)).all()

@router.post("/requirements", response_model=List[StaffingRequirement])
def set_requirements(reqs: List[RequirementCreate], session: Session = Depends(get_session), _: User = Depends(get_manager_user)):
    results = []
    for r in reqs:
        # Check if exists to update or create simple upsert logic
        existing = session.exec(select(StaffingRequirement).where(
            StaffingRequirement.date == r.date,
            StaffingRequirement.shift_def_id == r.shift_def_id,
            StaffingRequirement.role_id == r.role_id
        )).first()
        
        if existing:
            existing.min_count = r.min_count
            session.add(existing)
            results.append(existing)
        else:
            new_req = StaffingRequirement(
                date=r.date,
                shift_def_id=r.shift_def_id,
                role_id=r.role_id,
                min_count=r.min_count
            )
            session.add(new_req)
            results.append(new_req)
            
    session.commit()
    for res in results:
        session.refresh(res)
    return results

@router.get("/requirements", response_model=List[StaffingRequirement])
def get_requirements(start_date: date, end_date: date, session: Session = Depends(get_session), _: User = Depends(get_manager_user)):
    return session.exec(select(StaffingRequirement).where(
        StaffingRequirement.date >= start_date,
        StaffingRequirement.date <= end_date
    )).all()

class UserRoleLink(BaseModel):
    user_id: UUID
    role_id: int

@router.post("/users/roles")
def assign_role_to_user(link: UserRoleLink, session: Session = Depends(get_session), _: User = Depends(get_manager_user)):
    # We need to manually create the link in the link table or append to user.job_roles
    # SQLModel link adjustment
    from ..models import UserJobRoleLink
    
    # Check if exists
    existing = session.exec(select(UserJobRoleLink).where(
        UserJobRoleLink.user_id == link.user_id,
        UserJobRoleLink.role_id == link.role_id
    )).first()
    
    if not existing:
        new_link = UserJobRoleLink(user_id=link.user_id, role_id=link.role_id)
        session.add(new_link)
        session.commit()
        return {"status": "assigned"}
    return {"status": "already_assigned"}

class UserRolesUpdate(BaseModel):
    role_ids: List[int]

@router.put("/users/{user_id}/roles")
def update_user_roles(
    user_id: UUID, 
    update: UserRolesUpdate, 
    session: Session = Depends(get_session), 
    _: User = Depends(get_manager_user)
):
    from ..models import UserJobRoleLink
    
    # 1. Delete existing links
    existing_links = session.exec(select(UserJobRoleLink).where(UserJobRoleLink.user_id == user_id)).all()
    for link in existing_links:
        session.delete(link)
    
    # 2. Add new links
    for role_id in update.role_ids:
        new_link = UserJobRoleLink(user_id=user_id, role_id=role_id)
        session.add(new_link)
        
    session.commit()
    return {"status": "updated", "role_ids": update.role_ids}

class PasswordReset(BaseModel):
    new_password: str

@router.put("/users/{user_id}/password")
def reset_user_password(
    user_id: UUID, 
    reset: PasswordReset,
    session: Session = Depends(get_session),
    _: User = Depends(get_manager_user)
):
    from ..auth_utils import get_password_hash
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.password_hash = get_password_hash(reset.new_password)
    session.add(user)
    session.commit()
    
    return {"status": "password_reset_success"}

    return result

# --- Restaurant Config ---
from ..models import RestaurantConfig

class ConfigUpdate(BaseModel):
    name: str
    opening_hours: str # JSON
    address: Optional[str] = None

@router.get("/config", response_model=RestaurantConfig)
def get_config(session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    config = session.get(RestaurantConfig, 1)
    if not config:
        # Return default if not exists
        return RestaurantConfig(name="My Restaurant")
    return config

@router.post("/config", response_model=RestaurantConfig)
def update_config(update: ConfigUpdate, session: Session = Depends(get_session), _: User = Depends(get_manager_user)):
    config = session.get(RestaurantConfig, 1)
    if not config:
        config = RestaurantConfig(id=1, **update.dict())
        session.add(config)
    else:
        config.name = update.name
        config.opening_hours = update.opening_hours
        config.address = update.address
        session.add(config)
    session.commit()
    session.refresh(config)
    return config

# --- CRUD Updates ---

@router.put("/roles/{role_id}", response_model=JobRole)
def update_role(role_id: int, role_in: JobRoleCreate, session: Session = Depends(get_session), _: User = Depends(get_manager_user)):
    role = session.get(JobRole, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    role.name = role_in.name
    role.color_hex = role_in.color_hex
    session.add(role)
    session.commit()
    session.refresh(role)
    return role

@router.delete("/roles/{role_id}")
def delete_role(role_id: int, session: Session = Depends(get_session), _: User = Depends(get_manager_user)):
    role = session.get(JobRole, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    # Check usage? For MVP just delete (might fail constraint if DB enforced)
    try:
        session.delete(role)
        session.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot delete role: {str(e)}")
    return {"status": "deleted"}

@router.put("/shifts/{shift_id}", response_model=ShiftDefinition)
def update_shift(shift_id: int, shift_in: ShiftDefCreate, session: Session = Depends(get_session), _: User = Depends(get_manager_user)):
    shift = session.get(ShiftDefinition, shift_id)
    if not shift:
         raise HTTPException(status_code=404, detail="Shift not found")
    
    from datetime import datetime
    s_time = datetime.strptime(shift_in.start_time, "%H:%M").time()
    e_time = datetime.strptime(shift_in.end_time, "%H:%M").time()

    # Check for duplicates excluding self
    existing = session.exec(select(ShiftDefinition).where(
        ShiftDefinition.start_time == s_time,
        ShiftDefinition.end_time == e_time,
        ShiftDefinition.id != shift_id
    )).first()
    if existing:
        raise HTTPException(status_code=400, detail="Shift with these hours already exists")

    shift.name = shift_in.name
    shift.start_time = s_time
    shift.end_time = e_time
    session.add(shift)
    session.commit()
    session.refresh(shift)
    return shift

@router.delete("/shifts/{shift_id}")
def delete_shift(shift_id: int, session: Session = Depends(get_session), _: User = Depends(get_manager_user)):
    shift = session.get(ShiftDefinition, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    try:
        session.delete(shift)
        session.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot delete shift: {str(e)}")
    return {"status": "deleted"}
