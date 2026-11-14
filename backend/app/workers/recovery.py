"""
Worker reliability helpers:
- Persistent `WorkerJob` lifecycle tracking (`PENDING` -> `RUNNING`/`IN_PROGRESS` -> `COMPLETED`/`FAILED`).
- Safe transaction rollback and retry/requeue marking on errors or graceful shutdown interruption.
- Stale / Zombie job recovery at worker startup and periodically, with `ShiftAuditLog` and domain `log_event`.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import json
import logging
import os
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from ..database import engine
from ..models import RestaurantConfig, ShiftAuditLog, WorkerJob, WorkerJobStatus
from ..services.log_service import log_event
from . import get_stale_recovery_interval_sec, get_worker_job_timeout_sec

logger = logging.getLogger(__name__)

STALE_JOB_STATUSES = (WorkerJobStatus.RUNNING.value, WorkerJobStatus.IN_PROGRESS.value)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _use_requeue_on_stale() -> bool:
    return os.getenv("WORKER_STALE_RECOVERY_MODE", "fail").strip().lower() == "requeue"


def create_or_start_worker_job(
    session: Session,
    job_id: str,
    job_type: str,
    tenant_id: Optional[int] = None,
    payload: Optional[Dict[str, Any]] = None,
    status: str = WorkerJobStatus.RUNNING.value,
    max_retries: int = 3,
) -> WorkerJob:
    """Create or transition a `WorkerJob` record to `RUNNING` / `IN_PROGRESS`."""
    now = _utc_now()
    existing = session.exec(select(WorkerJob).where(WorkerJob.job_id == job_id)).first()
    payload_str = json.dumps(payload, default=str, ensure_ascii=False) if payload is not None else None
    if existing:
        existing.status = status
        existing.started_at = now
        existing.updated_at = now
        existing.error_message = None
        if payload_str is not None:
            existing.payload_json = payload_str
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    job = WorkerJob(
        job_id=job_id,
        tenant_id=tenant_id,
        job_type=job_type,
        status=status,
        payload_json=payload_str,
        max_retries=max_retries,
        started_at=now if status in STALE_JOB_STATUSES else None,
        created_at=now,
        updated_at=now,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def complete_worker_job(
    session: Session,
    job_id: str,
    result_summary: Optional[Dict[str, Any]] = None,
) -> Optional[WorkerJob]:
    """Mark a `WorkerJob` as `COMPLETED` and persist its telemetry/result summary."""
    job = session.exec(select(WorkerJob).where(WorkerJob.job_id == job_id)).first()
    if not job:
        return None
    now = _utc_now()
    job.status = WorkerJobStatus.COMPLETED.value
    job.finished_at = now
    job.updated_at = now
    job.error_message = None
    if result_summary is not None:
        job.result_summary_json = json.dumps(result_summary, default=str, ensure_ascii=False)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def fail_or_requeue_worker_job(
    session: Session,
    job_id: str,
    error_message: str,
    requeue: bool = False,
) -> Optional[WorkerJob]:
    """
    Safely rollback any broken transaction on `session`, then mark `WorkerJob` either
    for retry (`PENDING` with incremented `retry_count`) or as `FAILED`.
    """
    try:
        session.rollback()
    except Exception:
        pass

    job = session.exec(select(WorkerJob).where(WorkerJob.job_id == job_id)).first()
    if not job:
        return None

    now = _utc_now()
    if requeue and job.retry_count < job.max_retries:
        job.status = WorkerJobStatus.PENDING.value
        job.retry_count += 1
        job.started_at = None
        job.finished_at = None
        job.error_message = f"Requeued after interruption/error (attempt {job.retry_count}/{job.max_retries}): {error_message}"
    else:
        job.status = WorkerJobStatus.FAILED.value
        job.finished_at = now
        job.error_message = error_message

    job.updated_at = now
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def _record_stale_job_audit(
    session: Session,
    job: WorkerJob,
    prev_status: str,
    action: str,
    reason: str,
    now: datetime,
) -> None:
    """Persist ShiftAuditLog (when tenant exists) and domain log_event for a recovered stale job."""
    details = {
        "job_id": job.job_id,
        "job_type": job.job_type,
        "previous_status": prev_status,
        "new_status": job.status,
        "retry_count": job.retry_count,
        "max_retries": job.max_retries,
        "reason": reason,
        "recovered_at": now.isoformat(),
    }

    if job.tenant_id is not None:
        rest = session.get(RestaurantConfig, job.tenant_id)
        if rest is not None:
            session.add(
                ShiftAuditLog(
                    restaurant_id=job.tenant_id,
                    shift_id=f"worker_job:{job.job_id}",
                    date=now.date(),
                    changed_by_user_id=None,
                    action=action,
                    old_value=prev_status,
                    new_value=json.dumps(details, ensure_ascii=False),
                    summary=reason,
                )
            )

    category = "SOLVER" if job.job_type == "SOLVER" else "SYSTEM"
    level = "WARNING" if job.status == WorkerJobStatus.PENDING.value else "ERROR"
    log_event(
        category,
        f"Odzyskano zawieszone zadanie workera ({job.job_type}): {job.job_id} -> {job.status}",
        details,
        level=level,
        actor="System / Worker Recovery",
        tenant_id=job.tenant_id,
    )


def recover_stale_worker_jobs(
    session: Optional[Session] = None,
    timeout_sec: Optional[int] = None,
    requeue_retriable: Optional[bool] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Detect `WorkerJob` records stuck in `RUNNING` or `IN_PROGRESS` longer than `timeout_sec`
    and mark them as `FAILED` (with audit log) or requeue them (`PENDING`) when `requeue_retriable=True`.
    """
    effective_timeout = timeout_sec if timeout_sec is not None else get_worker_job_timeout_sec()
    effective_requeue = requeue_retriable if requeue_retriable is not None else _use_requeue_on_stale()
    current_time = _ensure_utc(now) or _utc_now()
    cutoff = current_time - timedelta(seconds=effective_timeout)

    own_session = False
    if session is None:
        session = Session(engine)
        own_session = True

    failed_ids: List[str] = []
    requeued_ids: List[str] = []

    try:
        candidates = session.exec(
            select(WorkerJob).where(WorkerJob.status.in_(STALE_JOB_STATUSES))
        ).all()

        for job in candidates:
            ref_ts = _ensure_utc(job.started_at) or _ensure_utc(job.updated_at) or _ensure_utc(job.created_at)
            if ref_ts is None or ref_ts > cutoff:
                continue

            prev_status = job.status
            elapsed_sec = round((current_time - ref_ts).total_seconds(), 1)

            if effective_requeue and job.retry_count < job.max_retries:
                job.status = WorkerJobStatus.PENDING.value
                job.retry_count += 1
                job.started_at = None
                reason = (
                    f"Zadanie {job.job_type} (job_id={job.job_id}) utknęło w statusie {prev_status} "
                    f"przez {elapsed_sec}s (limit {effective_timeout}s) — przywrócono do kolejki "
                    f"(próba {job.retry_count}/{job.max_retries})."
                )
                job.error_message = reason
                job.updated_at = current_time
                session.add(job)
                _record_stale_job_audit(
                    session, job, prev_status, "WORKER_JOB_STALE_REQUEUED", reason, current_time
                )
                requeued_ids.append(job.job_id)
                logger.warning(f"[WORKER RECOVERY] {reason}")
            else:
                job.status = WorkerJobStatus.FAILED.value
                job.finished_at = current_time
                reason = (
                    f"Zadanie {job.job_type} (job_id={job.job_id}) utknęło w statusie {prev_status} "
                    f"przez {elapsed_sec}s (limit {effective_timeout}s) — oznaczono jako FAILED."
                )
                job.error_message = reason
                job.updated_at = current_time
                session.add(job)
                _record_stale_job_audit(
                    session, job, prev_status, "WORKER_JOB_STALE_FAILED", reason, current_time
                )
                failed_ids.append(job.job_id)
                logger.error(f"[WORKER RECOVERY] {reason}")

        if failed_ids or requeued_ids:
            session.commit()

        return {
            "checked": len(candidates),
            "recovered_count": len(failed_ids) + len(requeued_ids),
            "failed_job_ids": failed_ids,
            "requeued_job_ids": requeued_ids,
            "timeout_sec": effective_timeout,
        }
    except Exception as exc:
        logger.error(f"[WORKER RECOVERY] Błąd podczas odzyskiwania zawieszonych zadań: {exc}", exc_info=True)
        try:
            session.rollback()
        except Exception:
            pass
        return {
            "checked": 0,
            "recovered_count": 0,
            "failed_job_ids": [],
            "requeued_job_ids": [],
            "timeout_sec": effective_timeout,
            "error": str(exc),
        }
    finally:
        if own_session:
            session.close()


async def periodic_stale_job_recovery_loop(
    stop_event: asyncio.Event,
    interval_sec: Optional[int] = None,
    timeout_sec: Optional[int] = None,
    requeue_retriable: Optional[bool] = None,
    run_on_startup: bool = True,
) -> None:
    """
    Run stale/zombie job recovery on startup (optional) and periodically every `interval_sec`
    until `stop_event` is set.
    """
    effective_interval = interval_sec if interval_sec is not None else get_stale_recovery_interval_sec()

    if run_on_startup and not stop_event.is_set():
        await asyncio.to_thread(
            recover_stale_worker_jobs,
            None,
            timeout_sec,
            requeue_retriable,
            None,
        )

    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=float(effective_interval))
            break
        except asyncio.TimeoutError:
            pass

        if stop_event.is_set():
            break

        await asyncio.to_thread(
            recover_stale_worker_jobs,
            None,
            timeout_sec,
            requeue_retriable,
            None,
        )
