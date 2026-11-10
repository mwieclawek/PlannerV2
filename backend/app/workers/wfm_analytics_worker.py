"""
WFM Analytics & Prediction Worker (`python -m app.workers.wfm_analytics_worker`).
- Consumes analytics and labor cost simulation tasks from RabbitMQ durable queue `wfm.analytics.tasks`
  with QoS `prefetch_count=1` and manual ACK (`message.process(requeue=True)`).
- Runs periodic background WFM bottleneck / attendance drift / shift stability prediction.
- Provides `run_wfm_analytics_job` with synchronous fallback when `USE_ASYNC_WORKER=false`.
"""
import asyncio
from datetime import date, datetime, time, timedelta
import json
import logging
import os
import signal
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlmodel import Session, select

from ..database import engine
from ..models import RestaurantConfig
from ..services.wfm_prediction_service import WFMPredictionService
from ..tenant_context import set_current_tenant_id
from . import use_async_worker
from .solver_worker import _run_coro_sync, get_rabbitmq_url

logger = logging.getLogger(__name__)

# Durable RabbitMQ AMQP queue for WFM Analytics & Prediction tasks
ANALYTICS_TASKS_QUEUE = "wfm.analytics.tasks"


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


def process_analytics_task_message(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single analytics task payload from `wfm.analytics.tasks`."""
    task_type = data.get("task", "wfm_analytics")
    tenant_id = data.get("tenant_id")
    s_date = date.fromisoformat(data["start_date"])
    e_date = date.fromisoformat(data["end_date"]) if data.get("end_date") else (s_date + timedelta(days=6))
    ref_date = date.fromisoformat(data["reference_date"]) if data.get("reference_date") else None
    draft_entries = data.get("draft_entries")

    if task_type == "labor_cost_simulation":
        return execute_labor_cost_simulation_sync(
            start_date=s_date,
            end_date=e_date,
            tenant_id=tenant_id,
            draft_entries=draft_entries,
            reference_date=ref_date,
            session=None,
            executed_via="async_worker",
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


async def _periodic_wfm_prediction_loop(stop_event: asyncio.Event, interval_sec: int = 1800) -> None:
    """Periodic background loop computing WFM bottleneck & drift diagnostics for active tenants."""
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=float(interval_sec))
            break
        except asyncio.TimeoutError:
            pass

        try:
            today = date.today()
            monday = today - timedelta(days=today.weekday())
            sunday = monday + timedelta(days=6)
            with Session(engine) as session:
                tenants = session.exec(select(RestaurantConfig)).all()
                for t in tenants:
                    if stop_event.is_set():
                        break
                    await asyncio.to_thread(
                        execute_wfm_analytics_sync,
                        monday,
                        sunday,
                        t.id,
                        None,
                        today,
                        None,
                        "periodic_analytics_worker",
                    )
        except Exception as exc:
            logger.debug(f"[WFM ANALYTICS WORKER] Okresowa predykcja WFM pominięta: {exc}")


async def run_analytics_worker_consumer(stop_event: Optional[asyncio.Event] = None) -> None:
    """
    Main async RabbitMQ consumer loop for the `analytics-worker` container.
    - Durable queue: `wfm.analytics.tasks`
    - QoS: `prefetch_count=1`
    - Manual ACK via `async with message.process(requeue=True):`
    """
    import aio_pika
    from aio_pika import DeliveryMode, Message

    rabbitmq_url = get_rabbitmq_url()
    logger.info(f"[WFM ANALYTICS WORKER] Uruchamianie konsumenta AMQP (queue={ANALYTICS_TASKS_QUEUE})...")

    if stop_event is None:
        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except NotImplementedError:
                signal.signal(sig, lambda *_: stop_event.set())

    periodic_task = asyncio.create_task(_periodic_wfm_prediction_loop(stop_event))

    try:
        while not stop_event.is_set():
            try:
                connection = await aio_pika.connect_robust(rabbitmq_url)
                async with connection:
                    channel = await connection.channel()
                    await channel.set_qos(prefetch_count=1)
                    tasks_queue = await channel.declare_queue(ANALYTICS_TASKS_QUEUE, durable=True)

                    logger.info(
                        f"[WFM ANALYTICS WORKER] Połączono z RabbitMQ. Nasłuchiwanie na trwałej kolejce '{ANALYTICS_TASKS_QUEUE}' (prefetch_count=1)..."
                    )

                    async with tasks_queue.iterator() as queue_iter:
                        async for message in queue_iter:
                            if stop_event.is_set():
                                break
                            async with message.process(requeue=True):
                                job_id = message.correlation_id or str(uuid4())
                                try:
                                    data = json.loads(message.body.decode("utf-8"))
                                    job_id = data.get("job_id") or job_id
                                    logger.info(
                                        f"[WFM ANALYTICS WORKER] Podjęto zadanie analityczne job_id={job_id} "
                                        f"(task={data.get('task')}) [tenant:{data.get('tenant_id')}]."
                                    )
                                    result = await asyncio.to_thread(process_analytics_task_message, data)
                                except Exception as exc:
                                    logger.error(
                                        f"[WFM ANALYTICS WORKER] Błąd wykonania zadania job_id={job_id}: {exc}",
                                        exc_info=True,
                                    )
                                    result = {"job_id": job_id, "status": "error", "detail": str(exc)}

                                if message.reply_to:
                                    await channel.default_exchange.publish(
                                        Message(
                                            body=json.dumps(result, default=_json_default).encode("utf-8"),
                                            correlation_id=job_id,
                                            content_type="application/json",
                                            delivery_mode=DeliveryMode.PERSISTENT,
                                        ),
                                        routing_key=message.reply_to,
                                    )
            except asyncio.CancelledError:
                break
            except Exception as conn_exc:
                if stop_event.is_set():
                    break
                logger.warning(
                    f"[WFM ANALYTICS WORKER] Problem z połączeniem RabbitMQ ({conn_exc}), ponawianie za 3s..."
                )
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=3.0)
                except asyncio.TimeoutError:
                    pass
    finally:
        periodic_task.cancel()
        try:
            await periodic_task
        except asyncio.CancelledError:
            pass

    logger.info("[WFM ANALYTICS WORKER] Proces analytics-worker zakończony.")


async def _dispatch_analytics_task_amqp(
    payload: Dict[str, Any],
    timeout_sec: int = 15,
) -> Dict[str, Any]:
    """Publish analytics task to `wfm.analytics.tasks` and await RPC response on exclusive reply queue."""
    import aio_pika
    from aio_pika import DeliveryMode, Message

    rabbitmq_url = get_rabbitmq_url()
    connection = await asyncio.wait_for(aio_pika.connect_robust(rabbitmq_url), timeout=3.0)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        await channel.declare_queue(ANALYTICS_TASKS_QUEUE, durable=True)
        reply_queue = await channel.declare_queue(exclusive=True, auto_delete=True)

        job_id = payload.get("job_id") or str(uuid4())
        body_bytes = json.dumps(payload, default=_json_default).encode("utf-8")
        await channel.default_exchange.publish(
            Message(
                body=body_bytes,
                correlation_id=job_id,
                reply_to=reply_queue.name,
                content_type="application/json",
                delivery_mode=DeliveryMode.PERSISTENT,
            ),
            routing_key=ANALYTICS_TASKS_QUEUE,
        )
        logger.info(
            f"[WFM ANALYTICS WORKER] Zadanie analityczne WFM wysłane do RabbitMQ '{ANALYTICS_TASKS_QUEUE}' "
            f"(job_id={job_id}) [tenant:{payload.get('tenant_id')}]."
        )

        async def _read_reply() -> Dict[str, Any]:
            async with reply_queue.iterator() as q_iter:
                async for msg in q_iter:
                    async with msg.process(requeue=False):
                        if msg.correlation_id == job_id:
                            return json.loads(msg.body.decode("utf-8"))
            raise TimeoutError(f"Brak odpowiedzi z {ANALYTICS_TASKS_QUEUE} dla job_id={job_id}")

        return await asyncio.wait_for(_read_reply(), timeout=float(timeout_sec))


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
    Dispatch WFM analytics & prediction task to the RabbitMQ `analytics-worker` when USE_ASYNC_WORKER=true,
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

    job_id = str(uuid4())
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
    try:
        parsed = _run_coro_sync(_dispatch_analytics_task_amqp(payload, timeout_sec=timeout_sec))
        if isinstance(parsed, dict) and parsed.get("status") != "error":
            parsed["executed_via"] = "async_worker"
            return parsed
    except Exception as exc:
        logger.warning(
            f"[WFM ANALYTICS WORKER] Brak połączenia z RabbitMQ/analytics-worker ({exc}), przejście na fallback synchroniczny."
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


if __name__ == "__main__":
    from ..services.log_service import (
        LOG_DIR,
        LOG_FILE,
        SqlNoiseFilter,
        TenantLogFilter,
        configure_noise_levels,
    )
    from logging.handlers import RotatingFileHandler

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

    logging.basicConfig(level=logging.INFO, handlers=[_stream_handler, _file_handler])
    configure_noise_levels()
    asyncio.run(run_analytics_worker_consumer())
