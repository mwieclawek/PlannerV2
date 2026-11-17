"""
Container & E2E smoke-check module (`python -m app.workers.smoke_check --mode=worker|backend-e2e`).

Used by unit tests, DEV/PROD CI/CD pre-flight image checks, and live container smoke tests:
- `worker`: verifies clean main-thread/worker-thread initialization of dateutil, pandas
  (`_pandas_datetime_CAPI`), and OR-Tools `cp_model`, and executes a real CP-SAT `solve_to_dto`
  optimization inside `asyncio.to_thread(...)`.
- `backend-e2e`: verifies in-process synchronous fallback (`solve_from_payload`) AND full
  end-to-end RabbitMQ RPC round-trip (`backend -> RabbitMQ wfm.solver.requests -> solver-worker`).
"""

import argparse
import asyncio
import sys
from typing import Any, Dict

from ..contracts.wfm import (
    SolverAvailabilityItem,
    SolverEmployeeItem,
    SolverInputDTO,
    SolverRequirementItem,
    SolverRoleItem,
    SolverShiftItem,
)
from ..services.solver import _load_cp_model, solve_from_payload, solve_to_dto


def build_smoke_solver_input() -> SolverInputDTO:
    """Create a deterministic minimal SolverInputDTO for smoke verification."""
    return SolverInputDTO(
        tenant_id=1,
        start_date="2026-11-30",
        end_date="2026-11-30",
        save=False,
        roles=[SolverRoleItem(id=1, name="SmokeRole")],
        shifts=[SolverShiftItem(id=1, name="SmokeShift", start_time="08:00", end_time="16:00")],
        employees=[SolverEmployeeItem(id="emp-1", full_name="Smoke Employee", role_ids=[1])],
        requirements=[SolverRequirementItem(date="2026-11-30", shift_def_id=1, role_id=1, min_count=1)],
        availabilities=[
            SolverAvailabilityItem(user_id="emp-1", date="2026-11-30", shift_def_id=1, status="AVAILABLE")
        ],
    )


def run_worker_smoke_check() -> Dict[str, Any]:
    """Verify dateutil/pandas/ortools initialization and solve a CP-SAT schedule in a worker thread."""
    cp_model = _load_cp_model()
    import dateutil.parser  # noqa: F401
    import dateutil.relativedelta  # noqa: F401
    import pandas as pd

    if not hasattr(pd, "_pandas_datetime_CAPI"):
        raise RuntimeError("Module 'pandas' is missing '_pandas_datetime_CAPI' (partial import detected).")
    if not hasattr(cp_model, "CpModel"):
        raise RuntimeError("Module 'ortools.sat.python.cp_model' is missing 'CpModel'.")

    payload = build_smoke_solver_input()

    async def _run_in_thread() -> Any:
        return await asyncio.to_thread(solve_to_dto, payload)

    res = asyncio.run(_run_in_thread())
    if res.status != "success" or res.count != 1:
        raise AssertionError(
            f"Unexpected solver smoke-check result: status={res.status!r}, count={res.count!r}"
        )
    return {
        "mode": "worker",
        "status": res.status,
        "assigned_count": res.count,
        "pandas_version": getattr(pd, "__version__", "unknown"),
    }


def run_backend_e2e_smoke_check(timeout_sec: int = 15) -> Dict[str, Any]:
    """
    Verify both local sync fallback (`solve_from_payload`) and live RabbitMQ RPC dispatch
    to the standalone `solver-worker` container.
    """
    from .solver_worker import _dispatch_solver_payload_amqp

    # 1. Verify in-process sync fallback inside the backend container
    local_payload = build_smoke_solver_input()
    sync_res = solve_from_payload(local_payload)
    if sync_res.get("status") != "success" or sync_res.get("count") != 1:
        raise AssertionError(f"Backend sync_fallback smoke check failed: {sync_res}")

    # 2. Verify live RabbitMQ AMQP RPC -> solver-worker -> reply queue
    amqp_payload = build_smoke_solver_input()
    rpc_res = asyncio.run(_dispatch_solver_payload_amqp(amqp_payload, timeout_sec=timeout_sec))
    if rpc_res.get("status") == "error":
        raise RuntimeError(f"AMQP solver-worker returned error: {rpc_res.get('detail')}")

    executed_via = (rpc_res.get("solver_explanation") or {}).get("executed_via")
    if rpc_res.get("status") != "success" or rpc_res.get("count") != 1 or executed_via != "async_worker":
        raise AssertionError(
            f"Backend E2E AMQP smoke check failed: status={rpc_res.get('status')!r}, "
            f"count={rpc_res.get('count')!r}, executed_via={executed_via!r}"
        )

    return {
        "mode": "backend-e2e",
        "sync_status": sync_res.get("status"),
        "amqp_status": rpc_res.get("status"),
        "executed_via": executed_via,
        "assigned_count": rpc_res.get("count"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PlannerV2 solver container & E2E smoke check")
    parser.add_argument(
        "--mode",
        choices=("worker", "backend-e2e"),
        default="worker",
        help="Verification mode: 'worker' (imports + CP-SAT in thread) or 'backend-e2e' (sync + RabbitMQ RPC)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="AMQP RPC timeout in seconds for backend-e2e mode (default: 15)",
    )
    args = parser.parse_args(argv)

    if args.mode == "worker":
        summary = run_worker_smoke_check()
    else:
        summary = run_backend_e2e_smoke_check(timeout_sec=args.timeout)

    print(f"[SMOKE CHECK OK] {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
