"""
Worker Orchestrator entrypoint (`python -m app.workers.main`).
In production (`docker-compose.yml` / `Jenkinsfile`), the two workers run as separate containers:
- `solver-worker`: `python -m app.workers.solver_worker` (built from `backend/Dockerfile.solver`, zero DB dependencies)
- `analytics-worker`: `python -m app.workers.wfm_analytics_worker` (built from `backend/Dockerfile`)
This module remains available for running both RabbitMQ consumers concurrently in a single development process,
with unified SIGINT/SIGTERM graceful shutdown and startup stale job recovery.
"""
import asyncio
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

from ..services.log_service import (
    LOG_DIR,
    LOG_FILE,
    SqlNoiseFilter,
    TenantLogFilter,
    configure_noise_levels,
)
from . import get_worker_shutdown_timeout_sec, install_signal_handlers
from .recovery import recover_stale_worker_jobs
from .solver_worker import (
    SOLVER_REQUESTS_QUEUE,
    SOLVER_RESULTS_QUEUE,
    process_solver_payload_message,
    run_solver_worker_consumer,
)
from .wfm_analytics_worker import (
    ANALYTICS_TASKS_QUEUE,
    process_analytics_task_message,
    run_analytics_worker_consumer,
)

os.makedirs(LOG_DIR, exist_ok=True)
_log_format = "%(asctime)s [%(levelname)s] [tenant:%(tenant_id)s] %(name)s: %(message)s"
_formatter = logging.Formatter(_log_format)

_stream_handler = logging.StreamHandler()
_stream_handler.setFormatter(_formatter)
_stream_handler.addFilter(TenantLogFilter())
_stream_handler.addFilter(SqlNoiseFilter())

_file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
_file_handler.setFormatter(_formatter)
_file_handler.addFilter(TenantLogFilter())
_file_handler.addFilter(SqlNoiseFilter())

logging.basicConfig(
    level=logging.INFO,
    handlers=[_stream_handler, _file_handler],
)
configure_noise_levels()
logger = logging.getLogger("app.workers.main")


async def run_all_workers(
    stop_event: Optional[asyncio.Event] = None,
    shutdown_timeout_sec: Optional[float] = None,
) -> None:
    """
    Run startup stale job recovery and orchestrate both worker consumers with
    graceful SIGINT/SIGTERM shutdown and bounded drain timeout.
    """
    if stop_event is None:
        stop_event = asyncio.Event()
    install_signal_handlers(stop_event, "WORKERS MAIN", logger)

    effective_shutdown_timeout = (
        shutdown_timeout_sec if shutdown_timeout_sec is not None else get_worker_shutdown_timeout_sec()
    )

    # Startup stale / zombie job recovery before accepting new work
    recovery_summary = await asyncio.to_thread(recover_stale_worker_jobs)
    if recovery_summary.get("recovered_count", 0) > 0:
        logger.warning(
            f"[WORKERS MAIN] Odzyskano zawieszone zadania przy starcie: {recovery_summary}"
        )

    solver_task = asyncio.create_task(run_solver_worker_consumer(stop_event), name="solver-worker")
    analytics_task = asyncio.create_task(run_analytics_worker_consumer(stop_event), name="analytics-worker")
    worker_tasks = [solver_task, analytics_task]

    stop_wait_task = asyncio.create_task(stop_event.wait(), name="stop-event-wait")
    try:
        done, _ = await asyncio.wait(
            [*worker_tasks, stop_wait_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        if stop_wait_task not in done:
            # One of the worker tasks exited unexpectedly; trigger shutdown for the other
            stop_event.set()
    finally:
        if not stop_wait_task.done():
            stop_wait_task.cancel()
            try:
                await stop_wait_task
            except asyncio.CancelledError:
                pass

    pending_workers = [t for t in worker_tasks if not t.done()]
    if pending_workers:
        logger.info(
            f"[WORKERS MAIN] Oczekiwanie do {effective_shutdown_timeout}s na dokończenie bieżących iteracji workerów..."
        )
        _, still_running = await asyncio.wait(
            pending_workers,
            timeout=effective_shutdown_timeout,
        )
        if still_running:
            logger.warning(
                f"[WORKERS MAIN] Przekroczono timeout graceful shutdown ({effective_shutdown_timeout}s) — "
                f"anulowanie {len(still_running)} zadań (transakcje zostaną wycofane i przywrócone do kolejki)."
            )
            for t in still_running:
                t.cancel()
            await asyncio.gather(*still_running, return_exceptions=True)

    await asyncio.gather(*worker_tasks, return_exceptions=True)
    logger.info("[WORKERS MAIN] Wszystkie procesy workerów zakończone bezpiecznie.")


if __name__ == "__main__":
    try:
        asyncio.run(run_all_workers())
    except KeyboardInterrupt:
        logger.info("[WORKERS MAIN] Przerwano przez KeyboardInterrupt.")
    sys.exit(0)
