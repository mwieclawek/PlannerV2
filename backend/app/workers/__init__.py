"""
Isolated Worker Service package for PlannerV2 (WFM CP-SAT Solver & WFM Analytics/Prediction).
Supports asynchronous execution via Redis/ARQ when USE_ASYNC_WORKER=true,
and synchronous in-process fallback when USE_ASYNC_WORKER=false (e.g. in pytest).
"""
import os


def use_async_worker() -> bool:
    """Return True only when USE_ASYNC_WORKER is explicitly enabled."""
    return os.getenv("USE_ASYNC_WORKER", "false").strip().lower() in ("true", "1", "yes")
