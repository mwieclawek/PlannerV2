"""
Isolated Worker Service package for PlannerV2:
- `solver-worker` (`python -m app.workers.solver_worker`): Stateless Pure-Compute OR-Tools CP-SAT microservice
  communicating exclusively over RabbitMQ AMQP (`wfm.solver.requests` -> `wfm.solver.results`).
- `analytics-worker` (`python -m app.workers.wfm_analytics_worker`): WFM Analytics & Prediction worker
  communicating over RabbitMQ AMQP (`wfm.analytics.tasks`).
- Supports synchronous in-process fallback when `USE_ASYNC_WORKER=false` (default in `pytest`).
"""
import asyncio
import logging
import os
import signal
from typing import Optional


def use_async_worker() -> bool:
    """Return True only when USE_ASYNC_WORKER is explicitly enabled."""
    return os.getenv("USE_ASYNC_WORKER", "false").strip().lower() in ("true", "1", "yes")


def get_worker_shutdown_timeout_sec() -> float:
    """Maximum seconds to wait for in-flight worker iterations during graceful shutdown."""
    try:
        return max(1.0, float(os.getenv("WORKER_SHUTDOWN_TIMEOUT_SEC", "30")))
    except (TypeError, ValueError):
        return 30.0


def get_worker_job_timeout_sec() -> int:
    """Maximum seconds a job may stay in RUNNING/IN_PROGRESS before stale recovery triggers."""
    try:
        return max(10, int(os.getenv("WORKER_JOB_TIMEOUT_SEC", "300")))
    except (TypeError, ValueError):
        return 300


def get_stale_recovery_interval_sec() -> int:
    """Interval in seconds between periodic stale/zombie job recovery sweeps."""
    try:
        return max(5, int(os.getenv("WORKER_STALE_RECOVERY_INTERVAL_SEC", "60")))
    except (TypeError, ValueError):
        return 60


def install_signal_handlers(
    stop_event: asyncio.Event,
    worker_name: str,
    log: Optional[logging.Logger] = None,
) -> None:
    """
    Register SIGINT and SIGTERM handlers that trigger `stop_event.set()` safely
    on both POSIX (`loop.add_signal_handler`) and Windows (`signal.signal` + `call_soon_threadsafe`).
    """
    target_logger = log or logging.getLogger(__name__)
    loop = asyncio.get_running_loop()

    def _on_signal(sig_num: int) -> None:
        try:
            sig_name = signal.Signals(sig_num).name
        except ValueError:
            sig_name = str(sig_num)
        if not stop_event.is_set():
            target_logger.info(
                f"[{worker_name}] Otrzymano sygnał {sig_name} — rozpoczynanie graceful shutdown..."
            )
            stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _on_signal, sig.value)
        except (NotImplementedError, RuntimeError, ValueError):
            def _sync_handler(signum: int, _frame: object) -> None:
                try:
                    loop.call_soon_threadsafe(_on_signal, signum)
                except RuntimeError:
                    stop_event.set()

            try:
                signal.signal(sig, _sync_handler)
            except (ValueError, OSError):
                # signal.signal can only be called from the main thread
                pass
