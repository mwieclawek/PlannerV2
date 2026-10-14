from datetime import date
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, BackgroundTasks
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

from ..tenant_context import require_tenant

def get_scheduler_service(
    session: Session = Depends(get_session),
    tenant_id: int = Depends(require_tenant)
) -> SchedulerService:
    return SchedulerService(session, tenant_id)

@router.post("/generate")
def generate_schedule(
    req: GenerateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_manager_user),
    tenant_id: int = Depends(require_tenant),
):
    service = SolverService(session, tenant_id=tenant_id)
    # Draft Mode: Do not save to DB immediately
    result = service.solve(req.start_date, req.end_date, save=False)
    return result

@router.post("/save_batch")
def save_batch_schedule(
    batch: BatchSaveRequest,
    background_tasks: BackgroundTasks,
    service: SchedulerService = Depends(get_scheduler_service),
    _: User = Depends(get_manager_user)
):
    count = service.save_batch(batch, background_tasks)
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
    background_tasks: BackgroundTasks,
    service: SchedulerService = Depends(get_scheduler_service),
    current_user: User = Depends(get_manager_user)
):
    count = service.publish_schedule(start_date, end_date, background_tasks, changed_by_user_id=current_user.id)
    return {"status": "published", "count": count}

@router.post("/assignment")
def manual_assign(
    assign: ManualAssignment,
    background_tasks: BackgroundTasks,
    service: SchedulerService = Depends(get_scheduler_service),
    current_user: User = Depends(get_manager_user)
):
    return service.assign(assign, background_tasks, changed_by_user_id=current_user.id)

@router.delete("/assignment/{schedule_id}")
def remove_assignment(
    schedule_id: str,  # kept as str: a malformed id yields {"status": "not_found"} (API contract)
    background_tasks: BackgroundTasks,
    service: SchedulerService = Depends(get_scheduler_service),
    current_user: User = Depends(get_manager_user)
):
    try:
        sched_uuid = UUID(schedule_id)
    except ValueError:
        return {"status": "not_found"}
    return service.remove_assignment(sched_uuid, background_tasks, changed_by_user_id=current_user.id)
