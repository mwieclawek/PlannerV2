from datetime import date
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlmodel import Session
from ..database import get_session
from ..models import User
from ..routers.manager import get_manager_user
from ..services.solver import SolverService
from ..services.scheduler_service import SchedulerService
from ..workers.solver_worker import run_solver_job
from ..workers.wfm_analytics_worker import (
    run_wfm_analytics_job,
    execute_labor_cost_simulation_sync,
)
from ..schemas import (
    GenerateRequest, BatchSaveRequest, 
    ScheduleResponse, ManualAssignment,
    LaborCostSimulationRequest,
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
    # Draft Mode: Do not save to DB immediately; delegates to isolated worker or sync fallback
    result = run_solver_job(
        start_date=req.start_date,
        end_date=req.end_date,
        tenant_id=tenant_id,
        session=session,
        save=False,
        actor=current_user,
    )
    return result


@router.get("/wfm-predictions")
def get_wfm_predictions(
    start_date: date,
    end_date: Optional[date] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_manager_user),
    tenant_id: int = Depends(require_tenant),
):
    return run_wfm_analytics_job(
        start_date=start_date,
        end_date=end_date,
        tenant_id=tenant_id,
        session=session,
    )


@router.post("/simulate-labor-cost")
def simulate_labor_cost(
    req: LaborCostSimulationRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_manager_user),
    tenant_id: int = Depends(require_tenant),
):
    draft_items = (
        [
            {
                "date": item.date,
                "shift_def_id": item.shift_def_id,
                "user_id": str(item.user_id),
                "role_id": item.role_id,
            }
            for item in req.items
        ]
        if req.items is not None
        else None
    )
    return execute_labor_cost_simulation_sync(
        start_date=req.start_date,
        end_date=req.end_date,
        tenant_id=tenant_id,
        draft_entries=draft_items,
        session=session,
    )


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
