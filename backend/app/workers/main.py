"""
Worker Orchestrator entrypoint (`python -m app.workers.main`).
In production (`docker-compose.yml` / `Jenkinsfile`), the two workers run as separate containers:
- `solver-worker`: `python -m app.workers.solver_worker` (built from `backend/Dockerfile.solver`, zero DB dependencies)
- `analytics-worker`: `python -m app.workers.wfm_analytics_worker` (built from `backend/Dockerfile`)
This module remains available for running both RabbitMQ consumers concurrently in a single development process.
"""
import asyncio
import logging
import os
import signal
import sys
from logging.handlers import RotatingFileHandler
from typing import Any, Dict

from ..services.log_service import (
    LOG_DIR,
    LOG_FILE,
    SqlNoiseFilter,
    TenantLogFilter,
    configure_noise_levels,
)
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


async def run_all_workers() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            signal.signal(sig, lambda *_: stop_event.set())

    await asyncio.gather(
        run_solver_worker_consumer(stop_event),
        run_analytics_worker_consumer(stop_event),
    )


if __name__ == "__main__":
    asyncio.run(run_all_workers())
    sys.exit(0)
