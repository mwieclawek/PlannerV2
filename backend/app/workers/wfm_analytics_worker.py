from datetime import date, datetime, time, timedelta
import json
import logging
import os
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlmodel import Session

from ..database import engine
from ..services.wfm_prediction_service import WFMPredictionService
from ..tenant_context import set_current_tenant_id
from . import use_async_worker
from .solver_worker import REDIS_JOB_QUEUE_KEY, REDIS_RESULT_KEY_PREFIX

logger = logging.getLogger(__name__)


def _json_default(obj: Any) -> Any:
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, time):
        return obj.strftime("%H:%M:%S")
    if isinstance(obj, UUID):
        return str(obj)
    return str(obj)


def execute_wfm_analytics_sync(
    start_date: date,
    end_date: Optional[date] = None,
    tenant_id: Optional[int] = None,
    draft_entries: Optional[List[Dict[str, Any]]] = None,
    reference_date: Optional[date] = None,
    session: Optional[Session] = None,
    executed_via: str = "sync_fallback",
) -> Dict[str, Any]:
    """
    Execute WFM Analytics & Prediction tasks (Schedule, Availability, Attendance,
    LeaveRequest, ShiftGiveaway, Payroll) in-process.
    """
    if tenant_id is not None:
        set_current_tenant_id(tenant_id)

    own_session = False
    if session is None:
        session = Session(engine)
        own_session = True

    try:
        svc = WFMPredictionService(session, tenant_id=tenant_id)
        report = svc.get_full_wfm_prediction_report(
            start_date=start_date,
            end_date=end_date,
            draft_entries=draft_entries,
            reference_date=reference_date,
        )
        report["executed_via"] = executed_via
        return report
    finally:
        if own_session:
            session.close()


def execute_labor_cost_simulation_sync(
    start_date: date,
    end_date: date,
    tenant_id: Optional[int] = None,
    draft_entries: Optional[List[Dict[str, Any]]] = None,
    reference_date: Optional[date] = None,
    session: Optional[Session] = None,
    executed_via: str = "sync_fallback",
) -> Dict[str, Any]:
    """Execute Live Labor Cost Simulation using Payroll rates and Attendance drift."""
    if tenant_id is not None:
        set_current_tenant_id(tenant_id)

    own_session = False
    if session is None:
        session = Session(engine)
        own_session = True

    try:
        svc = WFMPredictionService(session, tenant_id=tenant_id)
        sim = svc.simulate_labor_cost(
            start_date=start_date,
            end_date=end_date,
            draft_entries=draft_entries,
            reference_date=reference_date,
        )
        sim["executed_via"] = executed_via
        return sim
    finally:
        if own_session:
            session.close()


async def arq_wfm_analytics_task(
    ctx: Dict[str, Any],
    tenant_id: Optional[int],
    start_date_iso: str,
    end_date_iso: Optional[str] = None,
    draft_entries: Optional[List[Dict[str, Any]]] = None,
    reference_date_iso: Optional[str] = None,
) -> Dict[str, Any]:
    """ARQ-compatible async worker task for WFM analytics & prediction."""
    s_date = date.fromisoformat(start_date_iso)
    e_date = date.fromisoformat(end_date_iso) if end_date_iso else (s_date + timedelta(days=6))
    ref_date = date.fromisoformat(reference_date_iso) if reference_date_iso else None
    res = execute_wfm_analytics_sync(
        start_date=s_date,
        end_date=e_date,
        tenant_id=tenant_id,
        draft_entries=draft_entries,
        reference_date=ref_date,
        session=None,
        executed_via="async_worker",
    )
    return json.loads(json.dumps(res, default=_json_default))


def run_wfm_analytics_job(
    start_date: date,
    end_date: Optional[date] = None,
    tenant_id: Optional[int] = None,
    draft_entries: Optional[List[Dict[str, Any]]] = None,
    reference_date: Optional[date] = None,
    session: Optional[Session] = None,
    timeout_sec: int = 15,
) -> Dict[str, Any]:
    """
    Dispatch WFM analytics & prediction task to the isolated Redis worker when USE_ASYNC_WORKER=true,
    or execute synchronously in-process when USE_ASYNC_WORKER=false.
    """
    week_end = end_date or (start_date + timedelta(days=6))
    if not use_async_worker():
        return execute_wfm_analytics_sync(
            start_date=start_date,
            end_date=week_end,
            tenant_id=tenant_id,
            draft_entries=draft_entries,
            reference_date=reference_date,
            session=session,
            executed_via="sync_fallback",
        )

    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        import redis

        r_client = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
        r_client.ping()
        job_id = str(uuid4())
        result_key = f"{REDIS_RESULT_KEY_PREFIX}{job_id}"
        payload = {
            "job_id": job_id,
            "task": "wfm_analytics",
            "tenant_id": tenant_id,
            "start_date": start_date.isoformat(),
            "end_date": week_end.isoformat(),
            "draft_entries": json.loads(json.dumps(draft_entries, default=_json_default))
            if draft_entries is not None
            else None,
            "reference_date": reference_date.isoformat() if reference_date else None,
        }
        r_client.rpush(REDIS_JOB_QUEUE_KEY, json.dumps(payload))
        logger.info(
            f"[WFM ANALYTICS WORKER] Zadanie analityczne WFM wysłane do kolejki Redis (job_id={job_id}) [tenant:{tenant_id}]."
        )

        popped = r_client.blpop(result_key, timeout=timeout_sec)
        if popped:
            _, raw_res = popped
            r_client.delete(result_key)
            parsed = json.loads(raw_res)
            if isinstance(parsed, dict):
                parsed["executed_via"] = "async_worker"
            return parsed

        logger.warning(
            f"[WFM ANALYTICS WORKER] Timeout oczekiwania na wynik z planner-worker (job_id={job_id}), przejście na fallback synchroniczny."
        )
    except Exception as exc:
        logger.warning(
            f"[WFM ANALYTICS WORKER] Brak połączenia z Redis/workerem ({exc}), przejście na fallback synchroniczny."
        )

    return execute_wfm_analytics_sync(
        start_date=start_date,
        end_date=week_end,
        tenant_id=tenant_id,
        draft_entries=draft_entries,
        reference_date=reference_date,
        session=session,
        executed_via="sync_fallback",
    )
