"""
WFM Analytics & Prediction Worker (`python -m app.workers.wfm_analytics_worker`).
- Consumes analytics and labor cost simulation tasks from RabbitMQ durable queue `wfm.analytics.tasks`
  with QoS `prefetch_count=1` and manual ACK (`message.process(requeue=True)`).
- Runs periodic background WFM bottleneck / attendance drift / shift stability prediction.
- Runs startup & periodic stale/zombie `WorkerJob` recovery.
- Supports graceful shutdown on SIGINT / SIGTERM: finishes in-flight iteration or rolls back & requeues.
- Provides `run_wfm_analytics_job` with synchronous fallback when `USE_ASYNC_WORKER=false`.
"""
import asyncio
from calendar import monthrange
from datetime import date, datetime, time, timedelta
import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlmodel import Session, select

from ..contracts.wfm import (
    WfmAttendanceItemDTO,
    WfmAvailabilityItemDTO,
    WfmEmployeeDTO,
    WfmGiveawayItemDTO,
    WfmLeaveRequestItemDTO,
    WfmPredictionInputDTO,
    WfmRequirementItemDTO,
    WfmRoleDTO,
    WfmScheduleItemDTO,
    WfmShiftDTO,
)
from ..database import engine
from ..models import (
    Attendance,
    AttendanceStatus,
    Availability,
    JobRole,
    LeaveRequest,
    LeaveStatus,
    RestaurantConfig,
    Schedule,
    ShiftDefinition,
    ShiftGiveaway,
    StaffingRequirement,
    User,
    WorkerJobType,
)
from ..services.wfm_prediction_service import WFMPredictionService
from ..tenant_context import get_current_tenant_id, set_current_tenant_id
from . import install_signal_handlers, use_async_worker
from .recovery import (
    complete_worker_job,
    create_or_start_worker_job,
    fail_or_requeue_worker_job,
    periodic_stale_job_recovery_loop,
)
from .solver_worker import _next_message_or_stop, _run_coro_sync, get_rabbitmq_url

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


def build_wfm_prediction_input(
    session: Session,
    tenant_id: Optional[int],
    start_date: date,
    end_date: Optional[date] = None,
    draft_entries: Optional[List[Dict[str, Any]]] = None,
    reference_date: Optional[date] = None,
    lookback_weeks_drift: int = 6,
    lookback_weeks_stability: int = 8,
    include_rest_of_month: bool = True,
) -> WfmPredictionInputDTO:
    """
    Warstwa orkiestracji DB -> DTO:
    pobiera wszystkie dane domenowe WFM z bazy PostgreSQL i buduje bezstanowy
    kontrakt `WfmPredictionInputDTO` dla silnika `WFMPredictionService`.
    """
    tid = tenant_id
    if tid is None:
        tid = get_current_tenant_id()
        if tid is None:
            first_rest = session.exec(select(RestaurantConfig)).first()
            if first_rest:
                tid = first_rest.id

    week_end = end_date or (start_date + timedelta(days=6))
    ref_date = reference_date or date.today()
    last_day_num = monthrange(start_date.year, start_date.month)[1]
    month_start = date(start_date.year, start_date.month, 1)
    month_end = date(start_date.year, start_date.month, last_day_num)
    horizon_end = max(week_end, month_end) if include_rest_of_month else week_end

    drift_start = ref_date - timedelta(days=max(4, min(8, lookback_weeks_drift)) * 7)
    stability_start = ref_date - timedelta(days=lookback_weeks_stability * 7)
    ref_month_start = date(ref_date.year, ref_date.month, 1)
    ref_month_end = date(ref_date.year, ref_date.month, monthrange(ref_date.year, ref_date.month)[1])

    sched_min = min(month_start, start_date, drift_start, stability_start, ref_month_start)
    sched_max = max(month_end, horizon_end, ref_date + timedelta(days=30), ref_month_end)

    emp_q = select(User)
    shift_q = select(ShiftDefinition)
    role_q = select(JobRole)
    if tid is not None:
        emp_q = emp_q.where(User.tenant_id == tid)
        shift_q = shift_q.where(ShiftDefinition.tenant_id == tid)
        role_q = role_q.where(JobRole.tenant_id == tid)

    employees = list(session.exec(emp_q).all())
    shifts = list(session.exec(shift_q).all())
    roles = list(session.exec(role_q).all())

    emp_ids = {e.id for e in employees}
    shift_ids = {s.id for s in shifts if s.id is not None}

    schedules = list(
        session.exec(
            select(Schedule).where(Schedule.date >= sched_min, Schedule.date <= sched_max)
        ).all()
    )
    if tid is not None:
        schedules = [s for s in schedules if s.user_id in emp_ids]

    giveaways = list(session.exec(select(ShiftGiveaway)).all())
    if tid is not None:
        giveaways = [g for g in giveaways if g.offered_by in emp_ids]

    sched_by_id = {s.id: s for s in schedules}
    for g in giveaways:
        if g.schedule_id not in sched_by_id:
            sch = session.get(Schedule, g.schedule_id)
            if sch and (tid is None or sch.user_id in emp_ids):
                schedules.append(sch)
                sched_by_id[sch.id] = sch

    availabilities = list(
        session.exec(
            select(Availability).where(
                Availability.date >= start_date,
                Availability.date <= horizon_end,
            )
        ).all()
    )
    if tid is not None:
        availabilities = [a for a in availabilities if a.user_id in emp_ids]

    leaves = list(
        session.exec(
            select(LeaveRequest).where(
                LeaveRequest.status == LeaveStatus.APPROVED,
                LeaveRequest.end_date >= start_date,
                LeaveRequest.start_date <= horizon_end,
            )
        ).all()
    )
    if tid is not None:
        leaves = [lr for lr in leaves if lr.user_id in emp_ids]

    specific_reqs = list(
        session.exec(
            select(StaffingRequirement).where(
                StaffingRequirement.date >= start_date,
                StaffingRequirement.date <= horizon_end,
            )
        ).all()
    )
    global_reqs = list(
        session.exec(
            select(StaffingRequirement).where(StaffingRequirement.day_of_week != None)
        ).all()
    )
    if tid is not None:
        specific_reqs = [r for r in specific_reqs if r.shift_def_id in shift_ids]
        global_reqs = [r for r in global_reqs if r.shift_def_id in shift_ids]

    attendances = list(
        session.exec(
            select(Attendance).where(
                Attendance.date >= drift_start,
                Attendance.date <= ref_date,
                Attendance.status == AttendanceStatus.CONFIRMED,
            )
        ).all()
    )
    if tid is not None:
        attendances = [a for a in attendances if a.user_id in emp_ids]

    emp_dtos = [
        WfmEmployeeDTO(
            id=e.id,
            full_name=e.full_name,
            is_active=bool(e.is_active),
            role_system=e.role_system.value if hasattr(e.role_system, "value") else str(e.role_system),
            target_hours_per_month=e.target_hours_per_month,
            hourly_rate=e.hourly_rate,
            role_ids=[r.id for r in (e.job_roles or []) if r.id is not None],
            role_hourly_rates=[
                float(r.hourly_rate) for r in (e.job_roles or []) if r.hourly_rate is not None
            ],
        )
        for e in employees
    ]

    shift_dtos = [
        WfmShiftDTO(
            id=s.id,
            name=s.name,
            start_time=s.start_time,
            end_time=s.end_time,
            applicable_days=(
                [link.day_of_week for link in s.days]
                if getattr(s, "days", None)
                else [0, 1, 2, 3, 4, 5, 6]
            ),
        )
        for s in shifts
        if s.id is not None
    ]

    role_dtos = [
        WfmRoleDTO(
            id=r.id,
            name=r.name,
            color_hex=r.color_hex,
            hourly_rate=r.hourly_rate,
        )
        for r in roles
        if r.id is not None
    ]

    schedule_dtos = [
        WfmScheduleItemDTO(
            id=s.id,
            date=s.date,
            shift_def_id=s.shift_def_id,
            user_id=s.user_id,
            role_id=s.role_id,
        )
        for s in schedules
    ]

    avail_dtos = [
        WfmAvailabilityItemDTO(
            user_id=a.user_id,
            date=a.date,
            shift_def_id=a.shift_def_id,
            status=a.status.value if hasattr(a.status, "value") else str(a.status),
        )
        for a in availabilities
    ]

    leave_dtos = [
        WfmLeaveRequestItemDTO(
            user_id=lr.user_id,
            start_date=lr.start_date,
            end_date=lr.end_date,
            status=lr.status.value if hasattr(lr.status, "value") else str(lr.status),
        )
        for lr in leaves
    ]

    req_dtos = [
        WfmRequirementItemDTO(
            date=r.date,
            day_of_week=r.day_of_week,
            shift_def_id=r.shift_def_id,
            role_id=r.role_id,
            min_count=r.min_count,
        )
        for r in [*global_reqs, *specific_reqs]
    ]

    att_dtos = [
        WfmAttendanceItemDTO(
            user_id=a.user_id,
            date=a.date,
            schedule_id=a.schedule_id,
            check_in=a.check_in,
            check_out=a.check_out,
            status=a.status.value if hasattr(a.status, "value") else str(a.status),
            is_absent=bool(getattr(a, "is_absent", False)),
        )
        for a in attendances
    ]

    giveaway_dtos = [
        WfmGiveawayItemDTO(schedule_id=g.schedule_id, offered_by=g.offered_by)
        for g in giveaways
    ]

    return WfmPredictionInputDTO(
        tenant_id=tid,
        start_date=start_date,
        end_date=week_end,
        reference_date=ref_date,
        lookback_weeks_drift=lookback_weeks_drift,
        lookback_weeks_stability=lookback_weeks_stability,
        include_rest_of_month=include_rest_of_month,
        employees=emp_dtos,
        shifts=shift_dtos,
        roles=role_dtos,
        schedules=schedule_dtos,
        availabilities=avail_dtos,
        leave_requests=leave_dtos,
        requirements=req_dtos,
        attendances=att_dtos,
        giveaways=giveaway_dtos,
        draft_entries=draft_entries,
    )


def execute_wfm_analytics_sync(
    start_date: date,
    end_date: Optional[date] = None,
    tenant_id: Optional[int] = None,
    draft_entries: Optional[List[Dict[str, Any]]] = None,
    reference_date: Optional[date] = None,
    session: Optional[Session] = None,
    executed_via: str = "sync_fallback",
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute WFM Analytics & Prediction tasks (Schedule, Availability, Attendance,
    LeaveRequest, ShiftGiveaway, Payroll) in-process with WorkerJob tracking & rollback safety.
    """
    if tenant_id is not None:
        set_current_tenant_id(tenant_id)

    own_session = False
    if session is None:
        session = Session(engine)
        own_session = True

    effective_job_id = job_id or str(uuid4())
    try:
        create_or_start_worker_job(
            session,
            job_id=effective_job_id,
            job_type=WorkerJobType.PREDICTION.value,
            tenant_id=tenant_id,
            payload={"start_date": start_date.isoformat(), "end_date": end_date.isoformat() if end_date else None},
        )
        input_dto = build_wfm_prediction_input(
            session=session,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            draft_entries=draft_entries,
            reference_date=reference_date,
        )
        report_dto = WFMPredictionService.get_full_wfm_prediction_report(input_dto)
        report = report_dto.model_dump(mode="json")
        report["executed_via"] = executed_via
        report.setdefault("job_id", effective_job_id)
        complete_worker_job(
            session,
            job_id=effective_job_id,
            result_summary={"executed_via": executed_via, "start_date": start_date.isoformat()},
        )
        return report
    except Exception as exc:
        fail_or_requeue_worker_job(
            session,
            job_id=effective_job_id,
            error_message=str(exc),
            requeue=(executed_via == "async_worker"),
        )
        raise
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
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute Live Labor Cost Simulation using Payroll rates and Attendance drift."""
    if tenant_id is not None:
        set_current_tenant_id(tenant_id)

    own_session = False
    if session is None:
        session = Session(engine)
        own_session = True

    effective_job_id = job_id or str(uuid4())
    try:
        create_or_start_worker_job(
            session,
            job_id=effective_job_id,
            job_type=WorkerJobType.LABOR_COST_SIMULATION.value,
            tenant_id=tenant_id,
            payload={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        )
        input_dto = build_wfm_prediction_input(
            session=session,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            draft_entries=draft_entries,
            reference_date=reference_date,
        )
        sim = WFMPredictionService.simulate_labor_cost(input_dto)
        sim["executed_via"] = executed_via
        sim.setdefault("job_id", effective_job_id)
        complete_worker_job(
            session,
            job_id=effective_job_id,
            result_summary={"executed_via": executed_via, "start_date": start_date.isoformat()},
        )
        return sim
    except Exception as exc:
        fail_or_requeue_worker_job(
            session,
            job_id=effective_job_id,
            error_message=str(exc),
            requeue=(executed_via == "async_worker"),
        )
        raise
    finally:
        if own_session:
            session.close()


def process_analytics_task_message(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single analytics task payload from `wfm.analytics.tasks`."""
    task_type = data.get("task", "wfm_analytics")
    tenant_id = data.get("tenant_id")
    job_id = data.get("job_id")
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
            job_id=job_id,
        )
    return execute_wfm_analytics_sync(
        start_date=s_date,
        end_date=e_date,
        tenant_id=tenant_id,
        draft_entries=draft_entries,
        reference_date=ref_date,
        session=None,
        executed_via="async_worker",
        job_id=job_id,
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
    - Runs startup & periodic stale/zombie `WorkerJob` recovery.
    - Durable queue: `wfm.analytics.tasks`, QoS: `prefetch_count=1`, manual ACK (`requeue=True`).
    - Graceful shutdown on SIGINT / SIGTERM: exits immediately when idle, or finishes current iteration.
    """
    import aio_pika
    from aio_pika import DeliveryMode, Message

    rabbitmq_url = get_rabbitmq_url()
    logger.info(f"[WFM ANALYTICS WORKER] Uruchamianie konsumenta AMQP (queue={ANALYTICS_TASKS_QUEUE})...")

    if stop_event is None:
        stop_event = asyncio.Event()
        install_signal_handlers(stop_event, "WFM ANALYTICS WORKER", logger)

    periodic_task = asyncio.create_task(_periodic_wfm_prediction_loop(stop_event))
    recovery_task = asyncio.create_task(periodic_stale_job_recovery_loop(stop_event, run_on_startup=True))

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
                        while not stop_event.is_set():
                            message = await _next_message_or_stop(queue_iter, stop_event)
                            if message is None:
                                break
                            async with message.process(requeue=True):
                                job_id = message.correlation_id or str(uuid4())
                                try:
                                    data = json.loads(message.body.decode("utf-8"))
                                    job_id = data.get("job_id") or job_id
                                    data["job_id"] = job_id
                                    logger.info(
                                        f"[WFM ANALYTICS WORKER] Podjęto zadanie analityczne job_id={job_id} "
                                        f"(task={data.get('task')}) [tenant:{data.get('tenant_id')}]."
                                    )
                                    result = await asyncio.to_thread(process_analytics_task_message, data)
                                except asyncio.CancelledError:
                                    logger.warning(
                                        f"[WFM ANALYTICS WORKER] Przerwano zadanie job_id={job_id} podczas shutdown — ponowne kolejkowanie (requeue)."
                                    )
                                    with Session(engine) as err_session:
                                        fail_or_requeue_worker_job(
                                            err_session,
                                            job_id=job_id,
                                            error_message="Interrupted by worker shutdown",
                                            requeue=True,
                                        )
                                    raise
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
        for bg_task in (periodic_task, recovery_task):
            bg_task.cancel()
            try:
                await bg_task
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
        job_id=job_id,
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
    import os

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
