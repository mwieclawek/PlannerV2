from datetime import date
from typing import List
from fastapi import APIRouter, Depends
from sqlmodel import Session
from ..database import get_session
from ..models import User
from ..routers.manager import get_manager_user
from ..services.solver import SolverService
from ..services.scheduler_service import SchedulerService
from ..schemas import (
    GenerateRequest, BatchSaveRequest, 
    ScheduleResponse, ManualAssignment
)

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

def get_scheduler_service(session: Session = Depends(get_session)) -> SchedulerService:
    return SchedulerService(session)

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

@router.post("/save_batch")
def save_batch_schedule(
    batch: BatchSaveRequest,
    service: SchedulerService = Depends(get_scheduler_service),
    _: User = Depends(get_manager_user)
):
    count = service.save_batch(batch)
    return {"status": "saved", "count": count}

@router.get("/list", response_model=List[ScheduleResponse])
def list_schedules(
    start_date: date,
    end_date: date,
    service: SchedulerService = Depends(get_scheduler_service),
    _: User = Depends(get_manager_user)
):
    return service.get_schedule_list(start_date, end_date)

@router.post("/publish")
def publish_schedule(
    start_date: date,
    end_date: date,
    service: SchedulerService = Depends(get_scheduler_service),
    _: User = Depends(get_manager_user)
):
    count = service.publish_schedule(start_date, end_date)
    return {"status": "published", "count": count}

@router.post("/assignment")
def manual_assign(
    assign: ManualAssignment,
    session: Session = Depends(get_session),
    _: User = Depends(get_manager_user)
):
    # This logic is small enough for now, or could move to SchedulerService
    # Keeping it simple for the moment but using schema
    from ..models import Schedule
    from sqlmodel import select
    
    existing_daily = session.exec(select(Schedule).where(
        Schedule.date == assign.date,
        Schedule.user_id == assign.user_id
    )).first()

    if existing_daily:
        existing_daily.shift_def_id = assign.shift_def_id
        existing_daily.role_id = assign.role_id
        session.add(existing_daily)
        session.commit()
        return {"status": "updated", "id": str(existing_daily.id)}
    else:
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
        return {"status": "created", "id": str(new_entry.id)}

@router.delete("/assignment/{schedule_id}")
def remove_assignment(
    schedule_id: str, # UUIDs are strings in path
    session: Session = Depends(get_session),
    _: User = Depends(get_manager_user)
):
    from ..models import Schedule
    import uuid
    
    try:
        u_id = uuid.UUID(schedule_id)
        entry = session.get(Schedule, u_id)
        if entry:
            session.delete(entry)
            session.commit()
            return {"status": "deleted"}
    except ValueError:
        pass
        
    return {"status": "not_found"}
