import asyncio
from datetime import date, datetime, time, timedelta, timezone
import json
from uuid import uuid4

import pytest
from sqlmodel import Session, select

from app.models import (
    Availability,
    AvailabilityStatus,
    JobRole,
    RestaurantConfig,
    RoleSystem,
    ShiftAuditLog,
    ShiftDefinition,
    ShiftRoleLink,
    StaffingRequirement,
    User,
    UserJobRoleLink,
    WorkerJob,
    WorkerJobStatus,
    WorkerJobType,
)
from app.services.solver import solve_from_payload
from app.workers import install_signal_handlers
from app.workers.main import run_all_workers
from app.workers.recovery import (
    complete_worker_job,
    create_or_start_worker_job,
    fail_or_requeue_worker_job,
    periodic_stale_job_recovery_loop,
    recover_stale_worker_jobs,
)
from app.workers.solver_worker import _next_message_or_stop, execute_solver_job_sync
from app.workers.wfm_analytics_worker import execute_wfm_analytics_sync


def test_recover_stale_worker_jobs_marks_failed_and_writes_audit_log(session: Session):
    tenant = session.exec(select(RestaurantConfig)).first()
    now = datetime.now(timezone.utc)
    stale_time = now - timedelta(minutes=10)
    fresh_time = now - timedelta(minutes=1)

    stale_running = WorkerJob(
        job_id="job-stale-running",
        tenant_id=tenant.id,
        job_type=WorkerJobType.SOLVER.value,
        status=WorkerJobStatus.RUNNING.value,
        started_at=stale_time,
        updated_at=stale_time,
        created_at=stale_time,
    )
    stale_in_progress = WorkerJob(
        job_id="job-stale-in-progress",
        tenant_id=tenant.id,
        job_type=WorkerJobType.PREDICTION.value,
        status=WorkerJobStatus.IN_PROGRESS.value,
        started_at=stale_time,
        updated_at=stale_time,
        created_at=stale_time,
    )
    fresh_running = WorkerJob(
        job_id="job-fresh-running",
        tenant_id=tenant.id,
        job_type=WorkerJobType.SOLVER.value,
        status=WorkerJobStatus.RUNNING.value,
        started_at=fresh_time,
        updated_at=fresh_time,
        created_at=fresh_time,
    )
    completed_old = WorkerJob(
        job_id="job-completed-old",
        tenant_id=tenant.id,
        job_type=WorkerJobType.SOLVER.value,
        status=WorkerJobStatus.COMPLETED.value,
        started_at=stale_time,
        finished_at=stale_time,
        updated_at=stale_time,
        created_at=stale_time,
    )
    session.add_all([stale_running, stale_in_progress, fresh_running, completed_old])
    session.commit()

    summary = recover_stale_worker_jobs(
        session=session,
        timeout_sec=300,
        requeue_retriable=False,
        now=now,
    )

    assert summary["recovered_count"] == 2
    assert set(summary["failed_job_ids"]) == {"job-stale-running", "job-stale-in-progress"}
    assert summary["requeued_job_ids"] == []

    session.refresh(stale_running)
    session.refresh(stale_in_progress)
    session.refresh(fresh_running)
    session.refresh(completed_old)

    assert stale_running.status == WorkerJobStatus.FAILED.value
    assert stale_running.finished_at is not None
    assert "300s" in (stale_running.error_message or "")

    assert stale_in_progress.status == WorkerJobStatus.FAILED.value
    assert fresh_running.status == WorkerJobStatus.RUNNING.value
    assert completed_old.status == WorkerJobStatus.COMPLETED.value

    audit_logs = session.exec(
        select(ShiftAuditLog).where(ShiftAuditLog.action == "WORKER_JOB_STALE_FAILED")
    ).all()
    assert len(audit_logs) == 2
    assert {a.shift_id for a in audit_logs} == {
        "worker_job:job-stale-running",
        "worker_job:job-stale-in-progress",
    }


def test_recover_stale_worker_jobs_requeue_mode_respects_max_retries(session: Session):
    tenant = session.exec(select(RestaurantConfig)).first()
    now = datetime.now(timezone.utc)
    stale_time = now - timedelta(minutes=8)

    retriable_job = WorkerJob(
        job_id="job-retriable",
        tenant_id=tenant.id,
        job_type=WorkerJobType.PREDICTION.value,
        status=WorkerJobStatus.RUNNING.value,
        retry_count=1,
        max_retries=3,
        started_at=stale_time,
        updated_at=stale_time,
        created_at=stale_time,
    )
    exhausted_job = WorkerJob(
        job_id="job-exhausted",
        tenant_id=tenant.id,
        job_type=WorkerJobType.SOLVER.value,
        status=WorkerJobStatus.IN_PROGRESS.value,
        retry_count=3,
        max_retries=3,
        started_at=stale_time,
        updated_at=stale_time,
        created_at=stale_time,
    )
    session.add_all([retriable_job, exhausted_job])
    session.commit()

    summary = recover_stale_worker_jobs(
        session=session,
        timeout_sec=300,
        requeue_retriable=True,
        now=now,
    )

    assert summary["recovered_count"] == 2
    assert summary["requeued_job_ids"] == ["job-retriable"]
    assert summary["failed_job_ids"] == ["job-exhausted"]

    session.refresh(retriable_job)
    session.refresh(exhausted_job)

    assert retriable_job.status == WorkerJobStatus.PENDING.value
    assert retriable_job.retry_count == 2
    assert retriable_job.started_at is None
    assert exhausted_job.status == WorkerJobStatus.FAILED.value

    requeue_audits = session.exec(
        select(ShiftAuditLog).where(ShiftAuditLog.action == "WORKER_JOB_STALE_REQUEUED")
    ).all()
    assert len(requeue_audits) == 1
    assert requeue_audits[0].shift_id == "worker_job:job-retriable"


def test_fail_or_requeue_worker_job_rolls_back_and_marks_retry(session: Session):
    tenant = session.exec(select(RestaurantConfig)).first()
    job = create_or_start_worker_job(
        session,
        job_id="job-rollback-test",
        job_type=WorkerJobType.SOLVER.value,
        tenant_id=tenant.id,
    )
    assert job.status == WorkerJobStatus.RUNNING.value

    # Simulate an uncommitted dirty change on the session before failure
    job.error_message = "partial_uncommitted_write"
    session.add(job)

    updated = fail_or_requeue_worker_job(
        session,
        job_id="job-rollback-test",
        error_message="DB connection lost",
        requeue=True,
    )
    assert updated is not None
    assert updated.status == WorkerJobStatus.PENDING.value
    assert updated.retry_count == 1
    assert "DB connection lost" in (updated.error_message or "")


def test_execute_solver_job_sync_error_marks_job_failed(session: Session, monkeypatch):
    def _boom(*args, **kwargs):
        raise RuntimeError("Simulated CP-SAT crash")

    monkeypatch.setattr("app.workers.solver_worker.solve_from_payload", _boom)

    with pytest.raises(RuntimeError, match="Simulated CP-SAT crash"):
        execute_solver_job_sync(
            start_date=date(2026, 11, 16),
            end_date=date(2026, 11, 16),
            tenant_id=1,
            save=False,
            session=session,
        )

    jobs = session.exec(select(WorkerJob)).all()
    assert len(jobs) == 1
    assert jobs[0].status == WorkerJobStatus.FAILED.value
    assert "Simulated CP-SAT crash" in (jobs[0].error_message or "")


def test_execute_wfm_analytics_sync_error_marks_job_for_retry_in_async_mode(session: Session, monkeypatch):
    def _boom(*args, **kwargs):
        raise RuntimeError("Prediction service failure")

    monkeypatch.setattr(
        "app.workers.wfm_analytics_worker.WFMPredictionService.get_full_wfm_prediction_report",
        _boom,
    )

    with pytest.raises(RuntimeError, match="Prediction service failure"):
        execute_wfm_analytics_sync(
            start_date=date(2026, 11, 16),
            end_date=date(2026, 11, 22),
            tenant_id=1,
            session=session,
            executed_via="async_worker",
            job_id="analytics-err-1",
        )

    job = session.exec(select(WorkerJob).where(WorkerJob.job_id == "analytics-err-1")).first()
    assert job is not None
    assert job.status == WorkerJobStatus.PENDING.value
    assert job.retry_count == 1
    assert "Prediction service failure" in (job.error_message or "")


def test_solver_telemetry_and_bottlenecks_persisted_in_audit_and_worker_job(session: Session):
    tenant = session.exec(select(RestaurantConfig)).first()

    role_chef = JobRole(name="Kucharz", color_hex="#ef4444", tenant_id=tenant.id)
    role_waiter = JobRole(name="Kelner", color_hex="#3b82f6", tenant_id=tenant.id)
    session.add_all([role_chef, role_waiter])
    session.commit()
    session.refresh(role_chef)
    session.refresh(role_waiter)

    shift = ShiftDefinition(
        name="Rano",
        start_time=time(8, 0),
        end_time=time(16, 0),
        tenant_id=tenant.id,
    )
    session.add(shift)
    session.commit()
    session.refresh(shift)

    session.add(ShiftRoleLink(shift_def_id=shift.id, role_id=role_chef.id))
    session.add(ShiftRoleLink(shift_def_id=shift.id, role_id=role_waiter.id))

    emp = User(
        username="jan_kucharz",
        password_hash="x",
        full_name="Jan Kucharz",
        role_system=RoleSystem.EMPLOYEE,
        tenant_id=tenant.id,
        is_active=True,
    )
    session.add(emp)
    session.commit()
    session.refresh(emp)
    session.add(UserJobRoleLink(user_id=emp.id, role_id=role_chef.id))

    target_day = date(2026, 11, 16)
    session.add(
        Availability(
            user_id=emp.id,
            date=target_day,
            shift_def_id=shift.id,
            status=AvailabilityStatus.AVAILABLE,
            tenant_id=tenant.id,
        )
    )
    session.add(
        StaffingRequirement(
            date=target_day,
            shift_def_id=shift.id,
            role_id=role_chef.id,
            min_count=1,
            tenant_id=tenant.id,
        )
    )
    # No employee has role_waiter -> guaranteed bottleneck!
    session.add(
        StaffingRequirement(
            date=target_day,
            shift_def_id=shift.id,
            role_id=role_waiter.id,
            min_count=1,
            tenant_id=tenant.id,
        )
    )
    session.commit()

    result = execute_solver_job_sync(
        start_date=target_day,
        end_date=target_day,
        tenant_id=tenant.id,
        save=False,
        session=session,
    )

    exp = result["solver_explanation"]
    assert exp["solver_status"] in ("OPTIMAL", "FEASIBLE")
    assert "wall_time_sec" in exp and isinstance(exp["wall_time_sec"], float)
    assert "objective_value" in exp and isinstance(exp["objective_value"], float)
    assert "telemetry" in exp
    assert exp["telemetry"]["solver_status"] == exp["solver_status"]
    assert exp["telemetry"]["wall_time_sec"] == exp["wall_time_sec"]
    assert exp["telemetry"]["objective_value"] == exp["objective_value"]

    bottlenecks = exp.get("bottlenecks", [])
    assert len(bottlenecks) == 1
    assert bottlenecks[0]["role_name"] == "Kelner"
    assert bottlenecks[0]["reason_code"] == "NO_EMPLOYEES_WITH_ROLE"
    assert bottlenecks[0]["missing"] == 1

    audit = session.exec(
        select(ShiftAuditLog).where(ShiftAuditLog.action == "SOLVER_CP_SAT_RUN")
    ).first()
    assert audit is not None
    audit_data = json.loads(audit.new_value)
    assert audit_data["solver_status"] == exp["solver_status"]
    assert audit_data["wall_time_sec"] == exp["wall_time_sec"]
    assert audit_data["objective_value"] == exp["objective_value"]
    assert audit_data["bottlenecks_count"] == 1
    assert audit_data["bottlenecks"][0]["role_name"] == "Kelner"

    worker_job = session.exec(select(WorkerJob)).first()
    assert worker_job is not None
    assert worker_job.status == WorkerJobStatus.COMPLETED.value
    job_summary = json.loads(worker_job.result_summary_json)
    assert job_summary["solver_status"] == exp["solver_status"]
    assert job_summary["wall_time_sec"] == exp["wall_time_sec"]
    assert job_summary["objective_value"] == exp["objective_value"]


@pytest.mark.asyncio
async def test_graceful_shutdown_next_message_or_stop_and_orchestrator(monkeypatch):
    stop_event = asyncio.Event()

    async def _slow_iter():
        await asyncio.sleep(5)
        yield "never-reached"

    q_iter = _slow_iter()
    stop_event.set()
    msg = await _next_message_or_stop(q_iter, stop_event)
    assert msg is None

    # Test run_all_workers finishes in-flight worker iteration gracefully on stop_event
    in_flight_finished = False
    startup_recovery_called = False

    def _fake_recovery(*args, **kwargs):
        nonlocal startup_recovery_called
        startup_recovery_called = True
        return {"checked": 0, "recovered_count": 0, "failed_job_ids": [], "requeued_job_ids": []}

    async def _fake_solver_consumer(ev: asyncio.Event):
        nonlocal in_flight_finished
        await ev.wait()
        await asyncio.sleep(0.05)
        in_flight_finished = True

    async def _fake_analytics_consumer(ev: asyncio.Event):
        await ev.wait()

    monkeypatch.setattr("app.workers.main.recover_stale_worker_jobs", _fake_recovery)
    monkeypatch.setattr("app.workers.main.run_solver_worker_consumer", _fake_solver_consumer)
    monkeypatch.setattr("app.workers.main.run_analytics_worker_consumer", _fake_analytics_consumer)

    ev = asyncio.Event()

    async def _trigger_stop():
        await asyncio.sleep(0.05)
        ev.set()

    await asyncio.gather(
        run_all_workers(stop_event=ev, shutdown_timeout_sec=2.0),
        _trigger_stop(),
    )
    assert startup_recovery_called is True
    assert in_flight_finished is True


@pytest.mark.asyncio
async def test_periodic_stale_job_recovery_loop_runs_on_startup_and_stops(monkeypatch):
    calls = 0

    def _fake_recover(*args, **kwargs):
        nonlocal calls
        calls += 1
        return {"checked": 0, "recovered_count": 0, "failed_job_ids": [], "requeued_job_ids": []}

    monkeypatch.setattr("app.workers.recovery.recover_stale_worker_jobs", _fake_recover)

    stop_event = asyncio.Event()

    async def _stop_soon():
        await asyncio.sleep(0.05)
        stop_event.set()

    await asyncio.gather(
        periodic_stale_job_recovery_loop(stop_event, interval_sec=10, run_on_startup=True),
        _stop_soon(),
    )
    assert calls == 1
