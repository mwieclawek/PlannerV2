"""
Stateless Pure-Compute CP-SAT Solver Worker (`python -m app.workers.solver_worker`).
- Consumes `SolverJobPayload` JSON messages from RabbitMQ durable queue `wfm.solver.requests`
  with QoS `prefetch_count=1` and manual ACK (`message.process(requeue=True)`).
- Runs OR-Tools CP-SAT via `solve_from_payload(payload)` with ZERO database connection.
- Publishes JSON results to RabbitMQ durable queue `wfm.solver.results`.
- Also provides `run_solver_job` for backend FastAPI integration (with synchronous fallback
  when `USE_ASYNC_WORKER=false`), persisting `WorkerJob` lifecycle and OR-Tools telemetry.
"""
import asyncio
from datetime import date, datetime, time
import json
import logging
import os
from typing import Any, Dict, Optional, Union
from uuid import UUID, uuid4

from ..contracts.wfm import SolverInputDTO as SolverJobPayload
from ..services.solver import solve_from_payload
from . import install_signal_handlers, use_async_worker

logger = logging.getLogger(__name__)

# Durable RabbitMQ AMQP queue names
SOLVER_REQUESTS_QUEUE = "wfm.solver.requests"
SOLVER_RESULTS_QUEUE = "wfm.solver.results"


def _json_default(obj: Any) -> Any:
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, time):
        return obj.strftime("%H:%M:%S")
    if isinstance(obj, UUID):
        return str(obj)
    return str(obj)


def get_rabbitmq_url() -> str:
    url = os.getenv("RABBITMQ_URL", "").strip()
    if url:
        return url
    user = os.getenv("RABBITMQ_DEFAULT_USER", "planner").strip()
    password = os.getenv("RABBITMQ_DEFAULT_PASS", "planner_secret").strip()
    host = os.getenv("RABBITMQ_HOST", "rabbitmq").strip()
    port = os.getenv("RABBITMQ_PORT", "5672").strip()
    return f"amqp://{user}:{password}@{host}:{port}/"


def process_solver_payload_message(raw_body: Union[bytes, str, Dict[str, Any], SolverJobPayload]) -> Dict[str, Any]:
    """
    Pure-compute handler for a single message from `wfm.solver.requests`:
    JSON-In (`SolverJobPayload`) -> OR-Tools CP-SAT -> JSON-Out (`dict`).
    Zero database imports or connections.
    """
    if isinstance(raw_body, bytes):
        raw_body = raw_body.decode("utf-8")
    result = solve_from_payload(raw_body)
    if "solver_explanation" in result and isinstance(result["solver_explanation"], dict):
        result["solver_explanation"]["executed_via"] = "async_worker"
    return result


async def _next_message_or_stop(queue_iter: Any, stop_event: asyncio.Event) -> Any:
    """
    Wait for the next AMQP message OR `stop_event` while idle.
    Returns `None` if `stop_event` fired while waiting or the iterator ended.
    """
    next_task = asyncio.create_task(queue_iter.__anext__())
    stop_task = asyncio.create_task(stop_event.wait())
    done, pending = await asyncio.wait(
        {next_task, stop_task},
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, StopAsyncIteration):
            pass

    if next_task not in done:
        return None
    try:
        return next_task.result()
    except StopAsyncIteration:
        return None


async def run_solver_worker_consumer(stop_event: Optional[asyncio.Event] = None) -> None:
    """
    Main async RabbitMQ consumer loop for the standalone `solver-worker` container.
    - Durable queues: `wfm.solver.requests`, `wfm.solver.results`
    - QoS: `prefetch_count=1` (1 heavy CP-SAT job per worker instance for horizontal scaling)
    - Graceful shutdown: exits immediately when idle on SIGINT/SIGTERM; if mid-solve,
      finishes the current iteration before exiting (or requeues via `requeue=True` on cancellation).
    """
    import aio_pika
    from aio_pika import DeliveryMode, Message

    rabbitmq_url = get_rabbitmq_url()
    logger.info(f"[SOLVER WORKER] Uruchamianie bezstanowego konsumenta AMQP (queue={SOLVER_REQUESTS_QUEUE})...")

    if stop_event is None:
        stop_event = asyncio.Event()
        install_signal_handlers(stop_event, "SOLVER WORKER", logger)

    while not stop_event.is_set():
        try:
            connection = await aio_pika.connect_robust(rabbitmq_url)
            async with connection:
                channel = await connection.channel()
                # QoS prefetch_count=1: one heavy CP-SAT optimization task at a time per worker
                await channel.set_qos(prefetch_count=1)

                requests_queue = await channel.declare_queue(SOLVER_REQUESTS_QUEUE, durable=True)
                await channel.declare_queue(SOLVER_RESULTS_QUEUE, durable=True)

                logger.info(
                    f"[SOLVER WORKER] Połączono z RabbitMQ. Nasłuchiwanie na trwałej kolejce '{SOLVER_REQUESTS_QUEUE}' (prefetch_count=1)..."
                )

                async with requests_queue.iterator() as queue_iter:
                    while not stop_event.is_set():
                        message = await _next_message_or_stop(queue_iter, stop_event)
                        if message is None:
                            break
                        # Manual ACK after computation completes; if interrupted/cancelled mid-solve, requeue=True returns message to queue
                        async with message.process(requeue=True):
                            job_id = message.correlation_id or str(uuid4())
                            reply_routing_key = message.reply_to or SOLVER_RESULTS_QUEUE
                            try:
                                raw_str = message.body.decode("utf-8")
                                payload_obj = SolverJobPayload.model_validate_json(raw_str)
                                job_id = payload_obj.job_id or job_id
                                logger.info(
                                    f"[SOLVER WORKER] Podjęto zadanie CP-SAT job_id={job_id} "
                                    f"({payload_obj.start_date}..{payload_obj.end_date}) [tenant:{payload_obj.tenant_id}]."
                                )
                                # Run CPU-bound CP-SAT in thread executor so AMQP heartbeats stay responsive
                                result = await asyncio.to_thread(process_solver_payload_message, payload_obj)
                            except asyncio.CancelledError:
                                logger.warning(
                                    f"[SOLVER WORKER] Przerwano zadanie CP-SAT job_id={job_id} podczas shutdown — ponowne kolejkowanie (requeue)."
                                )
                                raise
                            except Exception as exc:
                                logger.error(
                                    f"[SOLVER WORKER] Błąd obliczeń CP-SAT dla job_id={job_id}: {exc}",
                                    exc_info=True,
                                )
                                result = {
                                    "job_id": job_id,
                                    "status": "error",
                                    "detail": str(exc),
                                }

                            result_bytes = json.dumps(result, default=_json_default).encode("utf-8")
                            await channel.default_exchange.publish(
                                Message(
                                    body=result_bytes,
                                    correlation_id=job_id,
                                    content_type="application/json",
                                    delivery_mode=DeliveryMode.PERSISTENT,
                                ),
                                routing_key=reply_routing_key,
                            )
                            logger.info(
                                f"[SOLVER WORKER] Wynik zadania job_id={job_id} opublikowany do '{reply_routing_key}' (ACK)."
                            )
        except asyncio.CancelledError:
            break
        except Exception as conn_exc:
            if stop_event.is_set():
                break
            logger.warning(f"[SOLVER WORKER] Problem z połączeniem RabbitMQ ({conn_exc}), ponawianie za 3s...")
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=3.0)
            except asyncio.TimeoutError:
                pass

    logger.info("[SOLVER WORKER] Bezstanowy proces solver-worker zakończony.")


async def _dispatch_solver_payload_amqp(
    payload: SolverJobPayload,
    timeout_sec: int = 25,
) -> Dict[str, Any]:
    """
    Publish `SolverJobPayload` to durable queue `wfm.solver.requests` (DeliveryMode.PERSISTENT)
    and wait for the matching `correlation_id == payload.job_id` result on an exclusive temporary reply queue.
    """
    import aio_pika
    from aio_pika import DeliveryMode, Message

    rabbitmq_url = get_rabbitmq_url()
    connection = await asyncio.wait_for(aio_pika.connect_robust(rabbitmq_url), timeout=3.0)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        await channel.declare_queue(SOLVER_REQUESTS_QUEUE, durable=True)
        reply_queue = await channel.declare_queue(exclusive=True, auto_delete=True)

        body_bytes = payload.model_dump_json().encode("utf-8")
        await channel.default_exchange.publish(
            Message(
                body=body_bytes,
                correlation_id=payload.job_id,
                reply_to=reply_queue.name,
                content_type="application/json",
                delivery_mode=DeliveryMode.PERSISTENT,
            ),
            routing_key=SOLVER_REQUESTS_QUEUE,
        )
        logger.info(
            f"[SOLVER WORKER] Wysłano SolverJobPayload do RabbitMQ '{SOLVER_REQUESTS_QUEUE}' "
            f"(job_id={payload.job_id}, reply_to={reply_queue.name}) [tenant:{payload.tenant_id}]."
        )

        async def _read_reply() -> Dict[str, Any]:
            async with reply_queue.iterator() as q_iter:
                async for msg in q_iter:
                    async with msg.process(requeue=False):
                        if msg.correlation_id == payload.job_id:
                            return json.loads(msg.body.decode("utf-8"))
            raise TimeoutError(f"Brak odpowiedzi z {SOLVER_REQUESTS_QUEUE} dla job_id={payload.job_id}")

        return await asyncio.wait_for(_read_reply(), timeout=float(timeout_sec))


def _run_coro_sync(coro: Any) -> Any:
    """Execute an async coroutine from a synchronous context (even if an event loop is running in another/current thread)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


def _extract_solver_telemetry(
    start_date: date,
    end_date: date,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a structured OR-Tools execution telemetry payload from a solver result."""
    explanation = result.get("solver_explanation", {}) or {}
    telemetry = explanation.get("telemetry", {}) or {}
    bottlenecks = explanation.get("bottlenecks", [])
    if not bottlenecks and explanation.get("deficit_explanations"):
        bottlenecks = explanation["deficit_explanations"]

    solver_status = telemetry.get("solver_status") or explanation.get("solver_status") or str(result.get("status", "UNKNOWN")).upper()
    wall_time_sec = telemetry.get("wall_time_sec", explanation.get("wall_time_sec", explanation.get("solve_duration_sec", 0.0)))
    user_time_sec = telemetry.get("user_time_sec", explanation.get("user_time_sec", 0.0))
    objective_value = telemetry.get("objective_value", explanation.get("objective_value", 0.0))
    best_objective_bound = telemetry.get("best_objective_bound", explanation.get("best_objective_bound", 0.0))

    return {
        "range": f"{start_date.isoformat()}..{end_date.isoformat()}",
        "status": result.get("status"),
        "solver_status": solver_status,
        "assigned_count": result.get("count", 0),
        "warnings_count": len(result.get("warnings", [])),
        "coverage_pct": explanation.get("coverage_pct", 0.0),
        "solve_duration_sec": explanation.get("solve_duration_sec", 0.0),
        "wall_time_sec": wall_time_sec,
        "user_time_sec": user_time_sec,
        "objective_value": objective_value,
        "best_objective_bound": best_objective_bound,
        "variables_count": telemetry.get("variables_count", explanation.get("variables_count", 0)),
        "objective_terms_count": telemetry.get("objective_terms_count", explanation.get("objective_terms_count", 0)),
        "bottlenecks_count": len(bottlenecks),
        "bottlenecks": bottlenecks,
        "executed_via": explanation.get("executed_via"),
    }


def _record_solver_domain_log(
    session: Any,
    tenant_id: Optional[int],
    start_date: date,
    end_date: date,
    result: Dict[str, Any],
) -> None:
    """Persist domain audit log entry summarizing the CP-SAT solver run, OR-Tools telemetry, and bottlenecks."""
    if tenant_id is None or session is None:
        return
    try:
        from ..models import RestaurantConfig, ShiftAuditLog

        rest = session.get(RestaurantConfig, tenant_id)
        if not rest:
            return
        summary_payload = _extract_solver_telemetry(start_date, end_date, result)
        summary_text = (
            f"Solver CP-SAT ({summary_payload['solver_status']}): "
            f"wall_time={summary_payload['wall_time_sec']}s, "
            f"objective={summary_payload['objective_value']}, "
            f"przypisano={summary_payload['assigned_count']}, "
            f"wąskie gardła={summary_payload['bottlenecks_count']}"
        )
        audit_entry = ShiftAuditLog(
            restaurant_id=tenant_id,
            shift_id=f"solver:{start_date.isoformat()}_{end_date.isoformat()}",
            date=start_date,
            changed_by_user_id=None,
            action="SOLVER_CP_SAT_RUN",
            old_value=None,
            new_value=json.dumps(summary_payload, ensure_ascii=False, default=_json_default),
            summary=summary_text,
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
    session: Any = None,
    executed_via: str = "sync_fallback",
    actor: Any = None,
) -> Dict[str, Any]:
    """
    Build `SolverJobPayload` from DB, execute Pure-Compute `solve_from_payload(payload)` in-process,
    and finalize/persist results and telemetry in the backend DB session.
    """
    from sqlmodel import Session
    from ..database import engine
    from ..models import WorkerJobType
    from ..services.scheduler_service import SchedulerService
    from ..tenant_context import set_current_tenant_id
    from .recovery import complete_worker_job, create_or_start_worker_job, fail_or_requeue_worker_job

    if tenant_id is not None:
        set_current_tenant_id(tenant_id)

    own_session = False
    if session is None:
        session = Session(engine)
        own_session = True

    job_id: Optional[str] = None
    try:
        sched_svc = SchedulerService(session, tenant_id=tenant_id)
        payload = sched_svc.build_solver_job_payload(
            start_date=start_date,
            end_date=end_date,
            save=save,
        )
        job_id = payload.job_id
        create_or_start_worker_job(
            session,
            job_id=job_id,
            job_type=WorkerJobType.SOLVER.value,
            tenant_id=tenant_id,
            payload={"start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "save": save},
        )
        raw_result = solve_from_payload(payload)
        result = sched_svc.finalize_solver_result(
            raw_result,
            start_date=start_date,
            end_date=end_date,
            save=save,
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
        telemetry = _extract_solver_telemetry(start_date, end_date, result)
        complete_worker_job(session, job_id=job_id, result_summary=telemetry)
        _record_solver_domain_log(session, tenant_id, start_date, end_date, result)
        return result
    except Exception as exc:
        if job_id is not None:
            fail_or_requeue_worker_job(session, job_id=job_id, error_message=str(exc), requeue=False)
        else:
            try:
                session.rollback()
            except Exception:
                pass
        raise
    finally:
        if own_session:
            session.close()


def run_solver_job(
    start_date: date,
    end_date: date,
    tenant_id: Optional[int] = None,
    session: Any = None,
    save: bool = False,
    timeout_sec: int = 25,
    actor: Any = None,
) -> Dict[str, Any]:
    """
    1. When `USE_ASYNC_WORKER=false` (default in `pytest`), runs `execute_solver_job_sync` in-process.
    2. When `USE_ASYNC_WORKER=true`, fetches data in the backend (`SchedulerService.build_solver_job_payload`),
       publishes self-contained `SolverJobPayload` JSON to RabbitMQ `wfm.solver.requests`,
       receives the pure-compute JSON result from `wfm.solver.results`, and finalizes/logs in the backend DB.
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

    from sqlmodel import Session
    from ..database import engine
    from ..models import WorkerJobType
    from ..services.scheduler_service import SchedulerService
    from ..tenant_context import set_current_tenant_id
    from .recovery import complete_worker_job, create_or_start_worker_job, fail_or_requeue_worker_job

    if tenant_id is not None:
        set_current_tenant_id(tenant_id)

    own_session = False
    if session is None:
        session = Session(engine)
        own_session = True

    job_id: Optional[str] = None
    try:
        sched_svc = SchedulerService(session, tenant_id=tenant_id)
        payload = sched_svc.build_solver_job_payload(
            start_date=start_date,
            end_date=end_date,
            save=save,
        )
        job_id = payload.job_id
        create_or_start_worker_job(
            session,
            job_id=job_id,
            job_type=WorkerJobType.SOLVER.value,
            tenant_id=tenant_id,
            payload={"start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "save": save},
        )
        try:
            raw_result = _run_coro_sync(_dispatch_solver_payload_amqp(payload, timeout_sec=timeout_sec))
            if raw_result.get("status") == "error":
                raise RuntimeError(raw_result.get("detail", "Błąd w kontenerze solver-worker"))
            result = sched_svc.finalize_solver_result(
                raw_result,
                start_date=start_date,
                end_date=end_date,
                save=save,
                actor=actor,
            )
            result.setdefault("solver_explanation", {})["executed_via"] = "async_worker"
            telemetry = _extract_solver_telemetry(start_date, end_date, result)
            complete_worker_job(session, job_id=job_id, result_summary=telemetry)
            _record_solver_domain_log(session, tenant_id, start_date, end_date, result)
            return result
        except Exception as exc:
            logger.warning(
                f"[SOLVER WORKER] Problem z brokerem RabbitMQ / solver-worker ({exc}), przejście na fallback synchroniczny."
            )
            raw_result = solve_from_payload(payload)
            result = sched_svc.finalize_solver_result(
                raw_result,
                start_date=start_date,
                end_date=end_date,
                save=save,
                actor=actor,
            )
            result.setdefault("solver_explanation", {})["executed_via"] = "sync_fallback"
            telemetry = _extract_solver_telemetry(start_date, end_date, result)
            complete_worker_job(session, job_id=job_id, result_summary=telemetry)
            _record_solver_domain_log(session, tenant_id, start_date, end_date, result)
            return result
    except Exception as exc:
        if job_id is not None:
            fail_or_requeue_worker_job(session, job_id=job_id, error_message=str(exc), requeue=False)
        else:
            try:
                session.rollback()
            except Exception:
                pass
        raise
    finally:
        if own_session:
            session.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(run_solver_worker_consumer())
