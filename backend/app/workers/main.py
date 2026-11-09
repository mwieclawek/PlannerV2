"""
Isolated Worker Process entrypoint (`python -m app.workers.main`).
Executes CPU-bound WFM tasks (CP-SAT Solver & WFM Workforce Prediction/Analytics)
outside the main FastAPI/Uvicorn process via Redis queue / ARQ.
"""
from datetime import date
import json
import logging
import os
import signal
import sys
import time
from typing import Any, Dict

from .solver_worker import (
    REDIS_JOB_QUEUE_KEY,
    REDIS_RESULT_KEY_PREFIX,
    _json_default,
    arq_solve_schedule_task,
    execute_solver_job_sync,
)
from .wfm_analytics_worker import (
    arq_wfm_analytics_task,
    execute_labor_cost_simulation_sync,
    execute_wfm_analytics_sync,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [PLANNER-WORKER] %(name)s: %(message)s",
)
logger = logging.getLogger("app.workers.main")

_running = True


def _handle_sigterm(signum, frame):
    global _running
    logger.info(f"Otrzymano sygnał zatrzymania ({signum}). Zamykanie procesu planner-worker...")
    _running = False


class WorkerSettings:
    """ARQ WorkerSettings configuration for compatibility with `arq app.workers.main.WorkerSettings`."""
    functions = [arq_solve_schedule_task, arq_wfm_analytics_task]


def process_single_job(raw_payload: str) -> Dict[str, Any]:
    """Process a single JSON job payload from the Redis queue and return the result dict."""
    data = json.loads(raw_payload)
    task_type = data.get("task")
    tenant_id = data.get("tenant_id")

    if task_type == "solver_generate":
        s_date = date.fromisoformat(data["start_date"])
        e_date = date.fromisoformat(data["end_date"])
        save = bool(data.get("save", False))
        logger.info(
            f"Przetwarzanie zadania solver_generate ({s_date}..{e_date}) dla tenant_id={tenant_id}"
        )
        return execute_solver_job_sync(
            start_date=s_date,
            end_date=e_date,
            tenant_id=tenant_id,
            save=save,
            session=None,
            executed_via="async_worker",
        )

    elif task_type == "wfm_analytics":
        s_date = date.fromisoformat(data["start_date"])
        e_date = date.fromisoformat(data["end_date"]) if data.get("end_date") else None
        ref_date = date.fromisoformat(data["reference_date"]) if data.get("reference_date") else None
        draft_entries = data.get("draft_entries")
        logger.info(
            f"Przetwarzanie zadania wfm_analytics ({s_date}..{e_date}) dla tenant_id={tenant_id}"
        )
        return execute_wfm_analytics_sync(
            start_date=s_date,
            end_date=e_date,
            tenant_id=tenant_id,
            draft_entries=draft_entries,
            reference_date=ref_date,
            session=None,
            executed_via="async_worker",
        )

    elif task_type == "labor_cost_simulation":
        s_date = date.fromisoformat(data["start_date"])
        e_date = date.fromisoformat(data["end_date"])
        ref_date = date.fromisoformat(data["reference_date"]) if data.get("reference_date") else None
        draft_entries = data.get("draft_entries")
        return execute_labor_cost_simulation_sync(
            start_date=s_date,
            end_date=e_date,
            tenant_id=tenant_id,
            draft_entries=draft_entries,
            reference_date=ref_date,
            session=None,
            executed_via="async_worker",
        )

    else:
        raise ValueError(f"Unknown worker task type: {task_type}")


def run_worker_loop() -> None:
    """Main blocking Redis queue loop for the `planner-worker` container."""
    signal.signal(signal.SIGINT, _handle_sigterm)
    signal.signal(signal.SIGTERM, _handle_sigterm)

    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    logger.info(f"Uruchamianie usługi planner-worker (REDIS_URL={redis_url})...")

    import redis

    while _running:
        try:
            r_client = redis.Redis.from_url(redis_url, decode_responses=True)
            r_client.ping()
            logger.info("Połączono z Redis. Oczekiwanie na zadania CP-SAT i WFM Analytics...")

            while _running:
                popped = r_client.blpop(REDIS_JOB_QUEUE_KEY, timeout=5)
                if not popped:
                    continue

                _, raw_payload = popped
                job_id = None
                try:
                    payload_obj = json.loads(raw_payload)
                    job_id = payload_obj.get("job_id")
                    result = process_single_job(raw_payload)
                except Exception as job_exc:
                    logger.error(f"Błąd podczas wykonywania zadania w workerze: {job_exc}", exc_info=True)
                    result = {"status": "error", "detail": str(job_exc)}

                if job_id:
                    result_key = f"{REDIS_RESULT_KEY_PREFIX}{job_id}"
                    r_client.rpush(result_key, json.dumps(result, default=_json_default))
                    r_client.expire(result_key, 120)
        except Exception as conn_exc:
            if not _running:
                break
            logger.warning(f"Problem z połączeniem Redis ({conn_exc}), ponawianie za 3s...")
            time.sleep(3)

    logger.info("Proces planner-worker zakończony.")


if __name__ == "__main__":
    run_worker_loop()
    sys.exit(0)
