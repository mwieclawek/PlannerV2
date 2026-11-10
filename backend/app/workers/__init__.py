"""
Isolated Worker Service package for PlannerV2:
- `solver-worker` (`python -m app.workers.solver_worker`): Stateless Pure-Compute OR-Tools CP-SAT microservice
  communicating exclusively over RabbitMQ AMQP (`wfm.solver.requests` -> `wfm.solver.results`).
- `analytics-worker` (`python -m app.workers.wfm_analytics_worker`): WFM Analytics & Prediction worker
  communicating over RabbitMQ AMQP (`wfm.analytics.tasks`).
- Supports synchronous in-process fallback when `USE_ASYNC_WORKER=false` (default in `pytest`).
"""
import os


def use_async_worker() -> bool:
    """Return True only when USE_ASYNC_WORKER is explicitly enabled."""
    return os.getenv("USE_ASYNC_WORKER", "false").strip().lower() in ("true", "1", "yes")
