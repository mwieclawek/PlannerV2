from datetime import date
from typing import List, Any
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from ..database import get_session
from ..models import User, Schedule, ShiftDefinition, JobRole
from ..auth_utils import get_current_user
from ..routers.manager import get_manager_user
from ..services.solver import SolverService
from pydantic import BaseModel

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

class GenerateRequest(BaseModel):
    start_date: date
    end_date: date

@router.post("/generate")
def generate_schedule(
    req: GenerateRequest,
    session: Session = Depends(get_session),
    _: User = Depends(get_manager_user)
):
    service = SolverService(session)
    # Draft Mode: Do not save to DB immediately
    result = service.solve(req.start_date, req.end_date, save=False)
    return result

class ScheduleBatchItem(BaseModel):
    date: date
    shift_def_id: int
    user_id: UUID
    role_id: int

class BatchSaveRequest(BaseModel):
    start_date: date
    end_date: date
    items: List[ScheduleBatchItem]

@router.post("/save_batch")
def save_batch_schedule(
    batch: BatchSaveRequest,
    session: Session = Depends(get_session),
    _: User = Depends(get_manager_user)
):
    # 1. Clear existing in range
    statements = select(Schedule).where(
        Schedule.date >= batch.start_date, 
        Schedule.date <= batch.end_date
    )
    existing = session.exec(statements).all()
    for e in existing:
        session.delete(e)
    
    # 2. Add new items
    count = 0
    for item in batch.items:
        new_sched = Schedule(
            date=item.date,
            shift_def_id=item.shift_def_id,
            user_id=item.user_id,
            role_id=item.role_id,
            is_published=False
        )
        session.add(new_sched)
        count += 1
    
    session.commit()
    return {"status": "saved", "count": count}

@router.get("/list")
def list_schedules(
    start_date: date,
    end_date: date,
    session: Session = Depends(get_session),
    _: User = Depends(get_manager_user)
):
    # Fetch schedules with related entities
    # SQLModel doesn't support easy joining in the exec result directly mapped to custom Pydantic models easily without some manual work or response_model logic
    # We will fetch all and construct response
    
    query = select(Schedule).where(
        Schedule.date >= start_date,
        Schedule.date <= end_date
    )
    schedules = session.exec(query).all()
    
    # Pre-fetch definitions to avoid N+1 if lazy loading
    # Actually with SQLite/SQLModel default lazy loading might trigger per item
    # Let's just respond with what we have, relying on JSON serialization to trigger access if models are connected, 
    # OR better: construct a flat response list
    
    response = []
    for s in schedules:
        # Accessing relationships (s.user, s.shift etc) will trigger lazy load if not eager loaded
        # Since volume is small (weekly schedule), this is acceptable for V2 MVP
        response.append({
            "id": s.id,
            "date": s.date,
            "shift_def_id": s.shift_def_id,
            "user_id": s.user_id,
            "role_id": s.role_id,
            "is_published": s.is_published,
            # Flattened details
            "user_name": s.user.full_name if s.user else "Unknown",
            "role_name": session.get(JobRole, s.role_id).name if s.role_id else "?", # s.role relationship might be missing in Schedule model definition? let's check models.py thought memory
            "shift_name": session.get(ShiftDefinition, s.shift_def_id).name if s.shift_def_id else "?"
        })
        
    return response

@router.post("/publish")
def publish_schedule(
    start_date: date,
    end_date: date,
    session: Session = Depends(get_session),
    _: User = Depends(get_manager_user)
):
    # Update all schedules in range to is_published=True
    query = select(Schedule).where(
        Schedule.date >= start_date,
        Schedule.date <= end_date
    )
    schedules = session.exec(query).all()
    count = 0
    for s in schedules:
        s.is_published = True
        session.add(s)
        count += 1
    session.commit()
    return {"status": "published", "count": count}

class ManualAssignment(BaseModel):
    date: date
    shift_def_id: int
    user_id: UUID
    role_id: int

@router.post("/assignment")
def manual_assign(
    assign: ManualAssignment,
    session: Session = Depends(get_session),
    _: User = Depends(get_manager_user)
):
    # 1. Check if assignment exists - upsert logic
    # Pydantic handles UUID conversion automatically

    # Check for existing assignment for this user on this day (Constraint: 1 shift per day)
    existing_daily = session.exec(select(Schedule).where(
        Schedule.date == assign.date,
        Schedule.user_id == assign.user_id
    )).first()

    if existing_daily:
        # Update existing assignment (change shift or role)
        existing_daily.shift_def_id = assign.shift_def_id
        existing_daily.role_id = assign.role_id
        # Preserve is_published status or set to false? Let's keep it simple.
        session.add(existing_daily)
        session.commit()
        return {"status": "updated", "id": existing_daily.id}
    else:
        # Create new
        new_entry = Schedule(
            date=assign.date,
            shift_def_id=assign.shift_def_id,
            user_id=assign.user_id,
            role_id=assign.role_id,
            is_published=False 
        )
        session.add(new_entry)
        session.commit()
        session.refresh(new_entry)
        return {"status": "created", "id": new_entry.id}



@router.delete("/assignment/{schedule_id}")
def remove_assignment(
    schedule_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_manager_user)
):
    entry = session.get(Schedule, schedule_id)
    if entry:
        session.delete(entry)
        session.commit()
        return {"status": "deleted"}
    return {"status": "not_found"}
