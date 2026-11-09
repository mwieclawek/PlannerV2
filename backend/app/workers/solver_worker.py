from datetime import date, datetime, time
import json
import logging
import os
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlmodel import Session

from ..database import engine
from ..models import RestaurantConfig, ShiftAuditLog
from ..services.log_service import _resolve_actor
from ..services.scheduler_service import SchedulerService
from ..services.solver import SolverService
from ..tenant_context import set_current_tenant_id
from . import use_async_worker

logger = logging.getLogger(__name__)

REDIS_JOB_QUEUE_KEY = "plannerv2:wfm:jobs"
REDIS_RESULT_KEY_PREFIX = "plannerv2:wfm:result:"


def _json_default(obj: Any) -> Any:
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, time):
        return obj.strftime("%H:%M:%S")
    if isinstance(obj, UUID):
        return str(obj)
    return str(obj)


def _record_solver_domain_log(
    session: Session,
    tenant_id: Optional[int],
    start_date: date,
    end_date: date,
    result: Dict[str, Any],
) -> None:
    """Persist domain audit log entry summarizing the CP-SAT solver run and explanation."""
    if tenant_id is None:
        return
    try:
        rest = session.get(RestaurantConfig, tenant_id)
        if not rest:
            return
        explanation = result.get("solver_explanation", {})
        summary_payload = {
            "range": f"{start_date.isoformat()}..{end_date.isoformat()}",
            "status": result.get("status"),
            "solver_status": explanation.get("solver_status"),
            "assigned_count": result.get("count", 0),
            "warnings_count": len(result.get("warnings", [])),
            "coverage_pct": explanation.get("coverage_pct", 0.0),
            "solve_duration_sec": explanation.get("solve_duration_sec", 0.0),
        }
        audit_entry = ShiftAuditLog(
            restaurant_id=tenant_id,
            shift_id=f"solver:{start_date.isoformat()}_{end_date.isoformat()}",
            date=start_date,
            changed_by_user_id=None,
            action="SOLVER_CP_SAT_RUN",
            old_value=None,
            new_value=json.dumps(summary_payload, ensure_ascii=False),
        )
        session.add(audit_entry)
        session.commit()
    except Exception as exc:
        logger.warning(f"[SOLVER WORKER] Nie udało się zapisać wpisu ShiftAuditLog: {exc}")
        session.rollback()


def execute_solver_job_sync(
    start_date: date,
    end_date: date,
    tenant_id: Optional[int] = None,
    save: bool = False,
    session: Optional[Session] = None,
    executed_via: str = "sync_fallback",
    actor: Any = None,
) -> Dict[str, Any]:
    """Execute CP-SAT schedule generation directly in the provided or new DB session."""
    if tenant_id is not None:
        set_current_tenant_id(tenant_id)

    own_session = False
    if session is None:
        session = Session(engine)
        own_session = True

    try:
        sched_svc = SchedulerService(session, tenant_id=tenant_id)
        weekly_targets = sched_svc.compute_weekly_targets(start_date, end_date)
        solver_svc = SolverService(session, tenant_id=tenant_id)
        result = solver_svc.solve(
            start_date,
            end_date,
            save=save,
            weekly_targets=weekly_targets,
            actor=actor,
        )
        if "solver_explanation" not in result:
            result["solver_explanation"] = {
                "solver_status": result.get("status", "unknown").upper(),
                "assigned_count": result.get("count", 0),
                "warnings_count": len(result.get("warnings", [])),
                "domain_logs": [],
            }
        result["solver_explanation"]["executed_via"] = executed_via
        _record_solver_domain_log(session, tenant_id, start_date, end_date, result)
        return result
    finally:
        if own_session:
            session.close()


async def arq_solve_schedule_task(
    ctx: Dict[str, Any],
    tenant_id: Optional[int],
    start_date_iso: str,
    end_date_iso: str,
    save: bool = False,
) -> Dict[str, Any]:
    """ARQ-compatible async worker task for CP-SAT schedule generation."""
    s_date = date.fromisoformat(start_date_iso)
    e_date = date.fromisoformat(end_date_iso)
    res = execute_solver_job_sync(
        start_date=s_date,
        end_date=e_date,
        tenant_id=tenant_id,
        save=save,
        session=None,
        executed_via="async_worker",
    )
    return json.loads(json.dumps(res, default=_json_default))


def run_solver_job(
    start_date: date,
    end_date: date,
    tenant_id: Optional[int] = None,
    session: Optional[Session] = None,
    save: bool = False,
    timeout_sec: int = 25,
    actor: Any = None,
) -> Dict[str, Any]:
    """
    Dispatch CP-SAT solver job to the isolated Redis worker when USE_ASYNC_WORKER=true,
    or execute synchronously in-process when USE_ASYNC_WORKER=false (default in pytest).
    """
    if not use_async_worker():
        logger.debug(
            f"[SOLVER WORKER] USE_ASYNC_WORKER=false -> wykonanie synchroniczne (fallback) dla {start_date}..{end_date} [tenant:{tenant_id}]."
        )
        return execute_solver_job_sync(
            start_date=start_date,
            end_date=end_date,
            tenant_id=tenant_id,
            save=save,
            session=session,
            executed_via="sync_fallback",
            actor=actor,
        )

    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        import redis

        r_client = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
        r_client.ping()
        job_id = str(uuid4())
        result_key = f"{REDIS_RESULT_KEY_PREFIX}{job_id}"
        actor_id, actor_name = _resolve_actor(actor)
        payload = {
            "job_id": job_id,
            "task": "solver_generate",
            "tenant_id": tenant_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "save": save,
            "actor": {"id": actor_id, "name": actor_name} if actor is not None else None,
        }
        r_client.rpush(REDIS_JOB_QUEUE_KEY, json.dumps(payload))
        logger.info(
            f"[SOLVER WORKER] Zadanie CP-SAT wysłane do kolejki Redis (job_id={job_id}) [tenant:{tenant_id}]."
        )

        popped = r_client.blpop(result_key, timeout=timeout_sec)
        if popped:
            _, raw_res = popped
            r_client.delete(result_key)
            parsed = json.loads(raw_res)
            if isinstance(parsed, dict) and "solver_explanation" in parsed:
                parsed["solver_explanation"]["executed_via"] = "async_worker"
            return parsed

        logger.warning(
            f"[SOLVER WORKER] Timeout oczekiwania na wynik z planner-worker (job_id={job_id}), przejście na fallback synchroniczny."
        )
    except Exception as exc:
        logger.warning(
            f"[SOLVER WORKER] Brak połączenia z Redis/workerem ({exc}), przejście na fallback synchroniczny."
        )

    return execute_solver_job_sync(
        start_date=start_date,
        end_date=end_date,
        tenant_id=tenant_id,
        save=save,
        session=session,
        executed_via="sync_fallback",
        actor=actor,
    )
