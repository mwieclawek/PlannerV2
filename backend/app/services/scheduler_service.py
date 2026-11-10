import calendar
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple
from uuid import UUID
from fastapi import HTTPException
from sqlmodel import Session, select
from ..models import (
    Schedule, User, JobRole, ShiftDefinition,
    Availability, AvailabilityStatus, LeaveRequest, LeaveStatus,
)
from ..schemas import BatchSaveRequest, ScheduleResponse
from .log_service import log_event
import logging

logger = logging.getLogger(__name__)


def _shift_duration_hours(shift: ShiftDefinition) -> float:
    start_dt = datetime.combine(date.today(), shift.start_time)
    end_dt = datetime.combine(date.today(), shift.end_time)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
    return (end_dt - start_dt).total_seconds() / 3600.0


def _compute_shift_overlaps(shifts: List[ShiftDefinition]) -> Set[Tuple[int, int]]:
    overlaps: Set[Tuple[int, int]] = set()
    for s1 in shifts:
        start1 = datetime.combine(date.today(), s1.start_time)
        end1 = datetime.combine(date.today(), s1.end_time)
        if end1 <= start1:
            end1 += timedelta(days=1)
        for s2 in shifts:
            if s1.id >= s2.id:
                continue
            start2 = datetime.combine(date.today(), s2.start_time)
            end2 = datetime.combine(date.today(), s2.end_time)
            if end2 <= start2:
                end2 += timedelta(days=1)
            latest_start = max(start1, start2)
            earliest_end = min(end1, end2)
            if latest_start < earliest_end:
                overlap_min = (earliest_end - latest_start).total_seconds() / 60.0
                is_enveloped = (start1 >= start2 and end1 <= end2) or (start2 >= start1 and end2 <= end1)
                if overlap_min > 30 or is_enveloped:
                    overlaps.add((s1.id, s2.id))
                    overlaps.add((s2.id, s1.id))
    return overlaps


def _max_non_overlapping_hours(
    shift_ids: List[int],
    shift_durations: Dict[int, float],
    overlaps: Set[Tuple[int, int]],
) -> float:
    if not shift_ids:
        return 0.0
    if len(shift_ids) == 1:
        return shift_durations.get(shift_ids[0], 0.0)
    best = 0.0
    n = len(shift_ids)

    def _dfs(idx: int, chosen: List[int], acc: float) -> None:
        nonlocal best
        if acc > best:
            best = acc
        for i in range(idx, n):
            sid = shift_ids[i]
            if all((sid, c) not in overlaps for c in chosen):
                chosen.append(sid)
                _dfs(i + 1, chosen, acc + shift_durations.get(sid, 0.0))
                chosen.pop()

    _dfs(0, [], 0.0)
    return min(best, 16.0)

class SchedulerService:
    def __init__(self, session: Session, tenant_id: Optional[int] = None):
        self.session = session
        if tenant_id is None:
            from ..tenant_context import get_current_tenant_id
            tid = get_current_tenant_id()
            if not tid:
                from ..models import RestaurantConfig
                first_rest = session.exec(select(RestaurantConfig)).first()
                if first_rest:
                    tid = first_rest.id
            self.tenant_id = tid
        else:
            self.tenant_id = tenant_id

    def _validate_batch_refs(self, items) -> None:
        """Reject batch items that reference users/shifts/roles of another tenant (IDOR)."""
        user_ids = {i.user_id for i in items}
        shift_ids = {i.shift_def_id for i in items}
        role_ids = {i.role_id for i in items}
        if user_ids:
            found = set(self.session.exec(
                select(User.id).where(User.id.in_(user_ids), User.tenant_id == self.tenant_id)
            ).all())
            if found != user_ids:
                raise HTTPException(status_code=404, detail="User not found")
        if shift_ids:
            found = set(self.session.exec(
                select(ShiftDefinition.id).where(
                    ShiftDefinition.id.in_(shift_ids), ShiftDefinition.tenant_id == self.tenant_id)
            ).all())
            if found != shift_ids:
                raise HTTPException(status_code=404, detail="Shift not found")
        if role_ids:
            found = set(self.session.exec(
                select(JobRole.id).where(JobRole.id.in_(role_ids), JobRole.tenant_id == self.tenant_id)
            ).all())
            if found != role_ids:
                raise HTTPException(status_code=404, detail="Role not found")

    def save_batch(self, batch: BatchSaveRequest, background_tasks=None) -> int:
        self._validate_batch_refs(batch.items)
        # 1. Clear existing in range
        statements = select(Schedule).join(User, Schedule.user_id == User.id).where(
            Schedule.date >= batch.start_date, 
            Schedule.date <= batch.end_date,
            User.tenant_id == self.tenant_id
        )
        existing = self.session.exec(statements).all()
        
        # Handle linked Attendance and ShiftAuditLog records (set schedule_id to None) to avoid FK violation
        existing_ids = [e.id for e in existing]
        existing_map = {e.id: e for e in existing}
        existing_str_map = {str(e.id): e for e in existing}
        if existing_ids:
            from ..models import Attendance, ShiftAuditLog
            linked_attendances = self.session.exec(
                select(Attendance).where(Attendance.schedule_id.in_(existing_ids))
            ).all()
            for att in linked_attendances:
                att.schedule_id = None
                self.session.add(att)
            linked_logs = self.session.exec(
                select(ShiftAuditLog).where(
                    (ShiftAuditLog.schedule_id.in_(existing_ids))
                    | (ShiftAuditLog.shift_id.in_(list(existing_str_map.keys())))
                )
            ).all()
            for log_row in linked_logs:
                sched_obj = (
                    existing_map.get(log_row.schedule_id)
                    if log_row.schedule_id
                    else existing_str_map.get(log_row.shift_id)
                )
                if sched_obj is not None:
                    if log_row.shift_def_id is None:
                        log_row.shift_def_id = sched_obj.shift_def_id
                    if log_row.date is None:
                        log_row.date = sched_obj.date
                log_row.schedule_id = None
                self.session.add(log_row)
            self.session.commit() # Commit updates to Attendance & ShiftAuditLog first
            
        # Published entries that are about to disappear must also vanish from Google Calendar
        removed_events = [(e.id, e.user_id) for e in existing if e.is_published]

        for e in existing:
            self.session.delete(e)
        
        # 2. Add new items
        count = 0
        new_entries = []
        is_published = getattr(batch, 'is_published', False)
        for item in batch.items:
            new_sched = Schedule(
                date=item.date,
                shift_def_id=item.shift_def_id,
                user_id=item.user_id,
                role_id=item.role_id,
                is_published=is_published
            )
            self.session.add(new_sched)
            new_entries.append((new_sched.id, new_sched.user_id, is_published))
            count += 1
        
        self.session.commit()

        # Google Calendar: drop stale events, create new ones (own session, primitive args only)
        from .google_calendar_service import enqueue, delete_event_task, sync_schedule_task
        for sched_id, user_id in removed_events:
            enqueue(background_tasks, delete_event_task, sched_id, user_id, self.tenant_id)
        for sched_id, user_id, pub in new_entries:
            if pub:
                enqueue(background_tasks, sync_schedule_task, sched_id, user_id, self.tenant_id)

        logger.info(
            f"[SCHEDULE] Zapisano partię grafiku od {batch.start_date} do {batch.end_date}. "
            f"Utworzono {count} pozycji (publikacja: {is_published}) [tenant:{self.tenant_id}]."
        )
        log_event(
            "SCHEDULE",
            "Zapisano grafik pracy (batch)",
            {
                "zakres": f"{batch.start_date} - {batch.end_date}",
                "liczba_zmian": count,
                "opublikowany": is_published,
            },
            tenant_id=self.tenant_id,
        )
        return count

    def compute_weekly_targets(
        self,
        start_date: date,
        end_date: date,
        employees: Optional[List[User]] = None,
        shifts: Optional[List[ShiftDefinition]] = None,
    ) -> Dict[UUID, Dict[str, Any]]:
        """
        Oblicza dla każdego aktywnego pracownika efektywny cel tygodniowy (effective_weekly_target)
        z uwzględnieniem kontekstu całego miesiąca kalendarzowego (lookahead dyspozycyjności i urlopów).
        """
        tid = self.tenant_id
        if employees is None:
            emp_q = select(User).where(User.is_active == True)
            if tid is not None:
                emp_q = emp_q.where(User.tenant_id == tid)
            employees = list(self.session.exec(emp_q).all())

        if shifts is None:
            shift_q = select(ShiftDefinition)
            if tid is not None:
                shift_q = shift_q.where(ShiftDefinition.tenant_id == tid)
            shifts = list(self.session.exec(shift_q).all())

        days = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
        month_start = date(start_date.year, start_date.month, 1)
        end_month_days = calendar.monthrange(end_date.year, end_date.month)[1]
        month_end = date(end_date.year, end_date.month, end_month_days)
        days_in_primary_month = calendar.monthrange(start_date.year, start_date.month)[1]

        shift_durations: Dict[int, float] = {s.id: _shift_duration_hours(s) for s in shifts}
        overlaps = _compute_shift_overlaps(shifts)
        shift_applicable_days: Dict[int, Set[int]] = {}
        for s in shifts:
            if hasattr(s, "days") and s.days:
                shift_applicable_days[s.id] = {link.day_of_week for link in s.days}
            else:
                shift_applicable_days[s.id] = set(range(7))

        emp_ids = {e.id for e in employees}
        if not emp_ids:
            return {}

        # a) worked_or_scheduled_hours: suma godzin zaplanowanych w miesiącu POZA [start_date, end_date]
        other_schedules = self.session.exec(
            select(Schedule).where(
                Schedule.date >= month_start,
                Schedule.date <= month_end,
                (Schedule.date < start_date) | (Schedule.date > end_date),
            )
        ).all()
        if tid is not None:
            other_schedules = [s for s in other_schedules if s.user_id in emp_ids]

        worked_or_scheduled_map: Dict[UUID, float] = {}
        for sc in other_schedules:
            dur = shift_durations.get(sc.shift_def_id)
            if dur is None:
                sh_obj = self.session.get(ShiftDefinition, sc.shift_def_id)
                dur = _shift_duration_hours(sh_obj) if sh_obj else 0.0
            worked_or_scheduled_map[sc.user_id] = worked_or_scheduled_map.get(sc.user_id, 0.0) + dur

        # Pobierz dostępności od start_date do końca miesiąca
        month_avails = self.session.exec(
            select(Availability).where(
                Availability.date >= start_date,
                Availability.date <= month_end,
            )
        ).all()
        if tid is not None:
            month_avails = [a for a in month_avails if a.user_id in emp_ids]

        avail_map: Dict[Tuple[str, str, int], str] = {}
        for a in month_avails:
            val = str(a.status.value) if hasattr(a.status, "value") else str(a.status)
            avail_map[(str(a.user_id), a.date.isoformat(), a.shift_def_id)] = val

        # Pobierz zatwierdzone urlopy (LeaveRequest) w zakresie [start_date, month_end]
        approved_leaves = self.session.exec(
            select(LeaveRequest).where(
                LeaveRequest.status == LeaveStatus.APPROVED,
                LeaveRequest.start_date <= month_end,
                LeaveRequest.end_date >= start_date,
            )
        ).all()
        if tid is not None:
            approved_leaves = [lr for lr in approved_leaves if lr.user_id in emp_ids]

        leaves_by_user: Dict[UUID, List[LeaveRequest]] = {}
        for lr in approved_leaves:
            leaves_by_user.setdefault(lr.user_id, []).append(lr)

        def _is_on_leave(u_id: UUID, d: date) -> bool:
            for lr in leaves_by_user.get(u_id, []):
                if lr.start_date <= d <= lr.end_date:
                    return True
            return False

        def _daily_avail_hours(emp: User, d: date) -> float:
            if _is_on_leave(emp.id, d):
                return 0.0
            if not getattr(emp, "job_roles", None):
                return 0.0
            dow = d.weekday()
            d_iso = d.isoformat()
            uid_str = str(emp.id)
            avail_sids: List[int] = []
            for s in shifts:
                if dow not in shift_applicable_days.get(s.id, set()):
                    continue
                st = avail_map.get((uid_str, d_iso, s.id), "UNKNOWN")
                if st in ("AVAILABLE", "PREFERRED"):
                    avail_sids.append(s.id)
            return _max_non_overlapping_hours(avail_sids, shift_durations, overlaps)

        future_days = [
            end_date + timedelta(days=i)
            for i in range(1, max(0, (month_end - end_date).days) + 1)
        ]
        future_chunks = [future_days[i:i + 7] for i in range(0, len(future_days), 7)]

        result: Dict[UUID, Dict[str, Any]] = {}
        for e in employees:
            monthly_target = float(e.target_hours_per_month) if e.target_hours_per_month is not None else None
            worked_hours = worked_or_scheduled_map.get(e.id, 0.0)
            remaining_monthly_target = (
                max(0.0, monthly_target - worked_hours) if monthly_target is not None else 0.0
            )

            current_week_avail_hours = sum(_daily_avail_hours(e, d) for d in days)

            # d) future_month_avail_hours z rozróżnieniem tygodni uzupełnionych vs nieuzupełnionych
            future_month_avail_hours = 0.0
            uid_str = str(e.id)
            for chunk in future_chunks:
                chunk_has_entries = any(
                    (uid_str, d.isoformat(), s.id) in avail_map
                    for d in chunk
                    for s in shifts
                )
                if chunk_has_entries:
                    future_month_avail_hours += sum(_daily_avail_hours(e, d) for d in chunk)
                else:
                    # Brak wpisów Availability w tym przyszłym tygodniu – nie zakładamy 0h!
                    est_daily = (
                        (monthly_target / float(days_in_primary_month))
                        if (monthly_target is not None and monthly_target > 0)
                        else (current_week_avail_hours / float(max(1, len(days))))
                    )
                    for d in chunk:
                        if _is_on_leave(e.id, d):
                            continue
                        future_month_avail_hours += est_daily

            if monthly_target is not None:
                denom = max(1.0, current_week_avail_hours + future_month_avail_hours)
                raw_weekly_target = remaining_monthly_target * (current_week_avail_hours / denom)
                max_shift_cap = (
                    float(e.target_shifts_per_month) * max(shift_durations.values(), default=8.0)
                    if e.target_shifts_per_month is not None
                    else 168.0
                )
                effective_weekly_target_hours = min(
                    raw_weekly_target,
                    current_week_avail_hours,
                    remaining_monthly_target,
                    max_shift_cap,
                )
                effective_weekly_target_minutes = int(round(effective_weekly_target_hours * 60))
                if current_week_avail_hours > 0:
                    scarcity_ratio = min(1.5, raw_weekly_target / max(1.0, current_week_avail_hours))
                else:
                    scarcity_ratio = 0.0
            else:
                raw_weekly_target = 0.0
                effective_weekly_target_hours = 0.0
                effective_weekly_target_minutes = 0
                scarcity_ratio = 0.0

            result[e.id] = {
                "user_id": e.id,
                "full_name": e.full_name,
                "monthly_target": monthly_target,
                "worked_or_scheduled_hours": round(worked_hours, 2),
                "remaining_monthly_target": round(remaining_monthly_target, 2),
                "current_week_avail_hours": round(current_week_avail_hours, 2),
                "future_month_avail_hours": round(future_month_avail_hours, 2),
                "raw_weekly_target_hours": round(raw_weekly_target, 2),
                "effective_weekly_target_hours": round(effective_weekly_target_hours, 2),
                "effective_weekly_target_minutes": effective_weekly_target_minutes,
                "scarcity_ratio": round(scarcity_ratio, 4),
            }

        return result

    def get_schedule_list(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        query = select(Schedule).join(User, Schedule.user_id == User.id).where(
            Schedule.date >= start_date,
            Schedule.date <= end_date,
            User.tenant_id == self.tenant_id
        )
        schedules = self.session.exec(query).all()
        
        response = []
        # Optimization: fetch all roles/shifts/users once if needed, but for weekly scale this is fine
        
        # Fetch active giveaways to mark them
        from ..models import ShiftGiveaway, GiveawayStatus
        giveaways = self.session.exec(
            select(ShiftGiveaway.schedule_id).where(
                ShiftGiveaway.status == GiveawayStatus.OPEN
            )
        ).all()
        giveaway_ids = set(str(g) for g in giveaways)

        for s in schedules:
            shift = self.session.get(ShiftDefinition, s.shift_def_id)
            response.append({
                "id": s.id,
                "date": s.date,
                "shift_def_id": s.shift_def_id,
                "user_id": s.user_id,
                "role_id": s.role_id,
                "is_published": s.is_published,
                "user_name": s.user.full_name if s.user else "Unknown",
                "role_name": self.session.get(JobRole, s.role_id).name if s.role_id else "?",
                "shift_name": shift.name if shift else "?",
                "start_time": shift.start_time if shift else None,
                "end_time": shift.end_time if shift else None,
                "is_on_giveaway": str(s.id) in giveaway_ids
            })
        return response

    def publish_schedule(self, start_date: date, end_date: date, background_tasks=None, changed_by_user_id: Optional[UUID] = None) -> int:
        from ..models import Notification, ShiftAuditLog
        
        query = select(Schedule).join(User, Schedule.user_id == User.id).where(
            Schedule.date >= start_date,
            Schedule.date <= end_date,
            User.tenant_id == self.tenant_id
        )
        schedules = self.session.exec(query).all()
        
        # Track which users get published schedules to notify them
        published_user_ids = set()
        
        count = 0
        for s in schedules:
            if not s.is_published:
                s.is_published = True
                self.session.add(s)
                published_user_ids.add(s.user_id)
                self.session.add(ShiftAuditLog(
                    restaurant_id=self.tenant_id,
                    shift_id=str(s.id),
                    schedule_id=s.id,
                    shift_def_id=s.shift_def_id,
                    date=s.date,
                    changed_by_user_id=changed_by_user_id,
                    action="PUBLISH",
                    old_value="is_published=False",
                    new_value="is_published=True"
                ))
                count += 1
                
        # Create notifications for affected users
        if background_tasks:
            from .push_service import PushService, send_push_to_tokens
            push_svc = PushService(self.session)
            
        for u_id in published_user_ids:
            title = "Nowy grafik opublikowany"
            body = f"Twój grafik na okres {start_date} - {end_date} został opublikowany."
            notif = Notification(
                user_id=u_id,
                title=title,
                body=body,
            )
            self.session.add(notif)
            
            if background_tasks:
                tokens = push_svc._get_user_tokens(u_id)
                if tokens:
                    background_tasks.add_task(send_push_to_tokens, tokens, title, body)

        self.session.commit()

        # Sync to Google Calendar AFTER commit, in the background, with its own session
        from .google_calendar_service import enqueue, sync_user_range_task
        all_published_user_ids = set(s.user_id for s in schedules if s.is_published)
        for u_id in all_published_user_ids:
            enqueue(background_tasks, sync_user_range_task, u_id, self.tenant_id, start_date, end_date)

        logger.info(
            f"[SCHEDULE] Opublikowano grafik na okres {start_date} - {end_date}. "
            f"Nowo opublikowanych zmian: {count}, powiadomiono pracowników: {len(published_user_ids)}, synchronizacja kalendarzy: {len(all_published_user_ids)} [tenant:{self.tenant_id}]."
        )
        actor_user = self.session.get(User, changed_by_user_id) if changed_by_user_id else None
        log_event(
            "SCHEDULE",
            "Opublikowano grafik pracy",
            {
                "zakres": f"{start_date} - {end_date}",
                "opublikowane_zmiany": count,
                "powiadomieni_pracownicy": len(published_user_ids),
            },
            actor=actor_user,
            tenant_id=self.tenant_id,
        )
        return count

    # --- Single assignment (manager) ---
    def assign(self, assign, background_tasks=None, changed_by_user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Create or update one schedule entry; every referenced object must be in this tenant."""
        self._validate_batch_refs([assign])
        from .google_calendar_service import enqueue, sync_schedule_task
        from ..models import ShiftAuditLog

        emp_obj = self.session.get(User, assign.user_id)
        shift_obj = self.session.get(ShiftDefinition, assign.shift_def_id)
        role_obj = self.session.get(JobRole, assign.role_id)
        actor_user = self.session.get(User, changed_by_user_id) if changed_by_user_id else None
        emp_label = emp_obj.full_name if emp_obj else str(assign.user_id)
        shift_label = shift_obj.name if shift_obj else str(assign.shift_def_id)
        role_label = role_obj.name if role_obj else str(assign.role_id)

        existing_daily = self.session.exec(select(Schedule).where(
            Schedule.date == assign.date,
            Schedule.user_id == assign.user_id
        )).first()

        if existing_daily:
            old_val = f"user_id={existing_daily.user_id}, role_id={existing_daily.role_id}, shift_def_id={existing_daily.shift_def_id}"
            existing_daily.shift_def_id = assign.shift_def_id
            existing_daily.role_id = assign.role_id
            self.session.add(existing_daily)
            new_val = f"user_id={assign.user_id}, role_id={assign.role_id}, shift_def_id={assign.shift_def_id}"
            self.session.add(ShiftAuditLog(
                restaurant_id=self.tenant_id,
                shift_id=str(existing_daily.id),
                schedule_id=existing_daily.id,
                shift_def_id=assign.shift_def_id,
                date=assign.date,
                changed_by_user_id=changed_by_user_id,
                action="ASSIGNMENT_CHANGE",
                old_value=old_val,
                new_value=new_val
            ))
            self.session.commit()
            if existing_daily.is_published:
                enqueue(background_tasks, sync_schedule_task, existing_daily.id, existing_daily.user_id, self.tenant_id)
            logger.info(
                f"[SCHEDULE] Zmiana przypisania dla pracownika (user_id={assign.user_id}) na datę {assign.date}: "
                f"zmiana={assign.shift_def_id}, rola={assign.role_id} (id={existing_daily.id}) [tenant:{self.tenant_id}]."
            )
            log_event(
                "SCHEDULE",
                "Zmodyfikowano przypisanie zmiany w grafiku",
                {
                    "pracownik": emp_label,
                    "data": str(assign.date),
                    "zmiana": shift_label,
                    "rola": role_label,
                },
                actor=actor_user,
                tenant_id=self.tenant_id,
            )
            return {"status": "updated", "id": str(existing_daily.id)}

        new_entry = Schedule(
            date=assign.date,
            shift_def_id=assign.shift_def_id,
            user_id=assign.user_id,
            role_id=assign.role_id,
            is_published=False
        )
        self.session.add(new_entry)
        self.session.flush()
        self.session.add(ShiftAuditLog(
            restaurant_id=self.tenant_id,
            shift_id=str(new_entry.id),
            schedule_id=new_entry.id,
            shift_def_id=assign.shift_def_id,
            date=assign.date,
            changed_by_user_id=changed_by_user_id,
            action="ASSIGNMENT_CHANGE",
            old_value=None,
            new_value=f"user_id={assign.user_id}, role_id={assign.role_id}, shift_def_id={assign.shift_def_id}"
        ))
        self.session.commit()
        self.session.refresh(new_entry)
        logger.info(
            f"[SCHEDULE] Nowe przypisanie dla pracownika (user_id={assign.user_id}) na datę {assign.date}: "
            f"zmiana={assign.shift_def_id}, rola={assign.role_id} (id={new_entry.id}) [tenant:{self.tenant_id}]."
        )
        log_event(
            "SCHEDULE",
            "Przypisano pracownika do zmiany",
            {
                "pracownik": emp_label,
                "data": str(assign.date),
                "zmiana": shift_label,
                "rola": role_label,
            },
            actor=actor_user,
            tenant_id=self.tenant_id,
        )
        return {"status": "created", "id": str(new_entry.id)}

    def remove_assignment(self, schedule_id: UUID, background_tasks=None, changed_by_user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Delete one schedule entry (tenant-scoped) and its Google Calendar event."""
        actor_user = self.session.get(User, changed_by_user_id) if changed_by_user_id else None
        entry = self.session.exec(
            select(Schedule).join(User, Schedule.user_id == User.id).where(
                Schedule.id == schedule_id, User.tenant_id == self.tenant_id
            )
        ).first()
        if not entry:
            logger.warning(f"[SCHEDULE ANOMALY] Próba usunięcia nieistniejącego lub obcego przypisania {schedule_id} [tenant:{self.tenant_id}].")
            log_event(
                "ANOMALY",
                "Próba usunięcia nieistniejącego lub obcego przypisania",
                {"schedule_id": str(schedule_id)},
                level="WARNING",
                actor=actor_user,
                tenant_id=self.tenant_id,
            )
            return {"status": "not_found"}

        was_published, user_id, sched_id, s_date = entry.is_published, entry.user_id, entry.id, entry.date
        emp_obj = self.session.get(User, user_id)
        shift_obj = self.session.get(ShiftDefinition, entry.shift_def_id)
        emp_label = emp_obj.full_name if emp_obj else str(user_id)
        shift_label = shift_obj.name if shift_obj else str(entry.shift_def_id)

        from ..models import Attendance, ShiftAuditLog
        prior_logs = self.session.exec(
            select(ShiftAuditLog).where(
                (ShiftAuditLog.schedule_id == sched_id) | (ShiftAuditLog.shift_id == str(sched_id))
            )
        ).all()
        for pl in prior_logs:
            if pl.shift_def_id is None:
                pl.shift_def_id = entry.shift_def_id
            if pl.date is None:
                pl.date = s_date
            pl.schedule_id = None
            self.session.add(pl)
        self.session.add(ShiftAuditLog(
            restaurant_id=self.tenant_id,
            shift_id=str(sched_id),
            schedule_id=None,
            shift_def_id=entry.shift_def_id,
            date=s_date,
            changed_by_user_id=changed_by_user_id,
            action="UNASSIGN",
            old_value=f"user_id={user_id}, role_id={entry.role_id}, shift_def_id={entry.shift_def_id}",
            new_value=None
        ))
        for att in self.session.exec(select(Attendance).where(Attendance.schedule_id == sched_id)).all():
            att.schedule_id = None
            self.session.add(att)
        self.session.flush()
        self.session.delete(entry)
        self.session.commit()

        if was_published:
            from .google_calendar_service import enqueue, delete_event_task
            enqueue(background_tasks, delete_event_task, sched_id, user_id, self.tenant_id)
        logger.info(f"[SCHEDULE] Usunięto przypisanie {sched_id} (user_id={user_id}, data={s_date}) [tenant:{self.tenant_id}].")
        log_event(
            "SCHEDULE",
            "Usunięto przypisanie z grafiku",
            {"pracownik": emp_label, "data": str(s_date), "zmiana": shift_label},
            actor=actor_user,
            tenant_id=self.tenant_id,
        )
        return {"status": "deleted"}

    def build_solver_job_payload(
        self,
        start_date: date,
        end_date: date,
        save: bool = False,
        weekly_targets: Optional[Dict[Any, Dict[str, Any]]] = None,
        job_id: Optional[str] = None,
    ) -> Any:
        """
        Pobiera z bazy PostgreSQL komplet danych potrzebnych do optymalizacji grafiku
        i buduje samowystarczalny obiekt `SolverJobPayload` dla bezstanowego `solver-worker`.
        """
        from uuid import uuid4
        from ..models import StaffingRequirement
        from .solver import (
            SolverAvailabilityItem,
            SolverEmployeeItem,
            SolverJobPayload,
            SolverLeaveDayItem,
            SolverRequirementItem,
            SolverRoleItem,
            SolverShiftItem,
        )

        tid = self.tenant_id
        emp_q = select(User).where(User.is_active == True)
        shift_q = select(ShiftDefinition)
        role_q = select(JobRole)
        if tid is not None:
            emp_q = emp_q.where(User.tenant_id == tid)
            shift_q = shift_q.where(ShiftDefinition.tenant_id == tid)
            role_q = role_q.where(JobRole.tenant_id == tid)

        employees = list(self.session.exec(emp_q).all())
        shifts = list(self.session.exec(shift_q).all())
        roles = list(self.session.exec(role_q).all())
        tenant_shift_ids = {s.id for s in shifts}
        emp_ids = {e.id for e in employees}

        if weekly_targets is None:
            weekly_targets = self.compute_weekly_targets(
                start_date, end_date, employees=employees, shifts=shifts
            )

        # Normalize weekly_targets keys to string UUIDs for JSON serialization
        serialized_wt: Dict[str, Dict[str, Any]] = {}
        for k, v in weekly_targets.items():
            row_copy = dict(v)
            if "user_id" in row_copy:
                row_copy["user_id"] = str(row_copy["user_id"])
            serialized_wt[str(k)] = row_copy

        delta = end_date - start_date
        days = [start_date + timedelta(days=i) for i in range(delta.days + 1)]

        # Operational availabilities
        availabilities = self.session.exec(
            select(Availability).where(
                Availability.date >= start_date,
                Availability.date <= end_date,
            )
        ).all()
        if tid is not None:
            availabilities = [a for a in availabilities if a.user_id in emp_ids]

        avail_items: List[SolverAvailabilityItem] = []
        for a in availabilities:
            val = str(a.status.value) if hasattr(a.status, "value") else str(a.status)
            avail_items.append(
                SolverAvailabilityItem(
                    user_id=str(a.user_id),
                    date=a.date.isoformat(),
                    shift_def_id=a.shift_def_id,
                    status=val,
                )
            )

        # Approved leaves in [start_date, end_date]
        approved_leaves = self.session.exec(
            select(LeaveRequest).where(
                LeaveRequest.status == LeaveStatus.APPROVED,
                LeaveRequest.start_date <= end_date,
                LeaveRequest.end_date >= start_date,
            )
        ).all()
        if tid is not None:
            approved_leaves = [lr for lr in approved_leaves if lr.user_id in emp_ids]

        leave_items: List[SolverLeaveDayItem] = []
        seen_leaves: Set[Tuple[str, str]] = set()
        for lr in approved_leaves:
            cur = max(start_date, lr.start_date)
            end_lr = min(end_date, lr.end_date)
            while cur <= end_lr:
                key_l = (str(lr.user_id), cur.isoformat())
                if key_l not in seen_leaves:
                    seen_leaves.add(key_l)
                    leave_items.append(SolverLeaveDayItem(user_id=key_l[0], date=key_l[1]))
                cur += timedelta(days=1)

        # Staffing requirements (global + specific overrides)
        specific_reqs = self.session.exec(
            select(StaffingRequirement).where(
                StaffingRequirement.date >= start_date,
                StaffingRequirement.date <= end_date,
            )
        ).all()
        if tid is not None:
            specific_reqs = [r for r in specific_reqs if r.shift_def_id in tenant_shift_ids]

        global_reqs = self.session.exec(
            select(StaffingRequirement).where(StaffingRequirement.day_of_week != None)
        ).all()
        if tid is not None:
            global_reqs = [r for r in global_reqs if r.shift_def_id in tenant_shift_ids]

        req_map: Dict[Tuple[str, int, int], int] = {}
        for d in days:
            dow = d.weekday()
            d_iso = d.isoformat()
            for r in global_reqs:
                if r.day_of_week == dow:
                    req_map[(d_iso, r.shift_def_id, r.role_id)] = r.min_count
        for r in specific_reqs:
            if r.date:
                req_map[(r.date.isoformat(), r.shift_def_id, r.role_id)] = r.min_count

        req_items: List[SolverRequirementItem] = [
            SolverRequirementItem(
                date=d_iso,
                shift_def_id=s_id,
                role_id=r_id,
                min_count=min_cnt,
            )
            for (d_iso, s_id, r_id), min_cnt in req_map.items()
        ]

        shift_items: List[SolverShiftItem] = []
        for s in shifts:
            if hasattr(s, "days") and s.days:
                app_days = [link.day_of_week for link in s.days]
            else:
                app_days = list(range(7))
            shift_items.append(
                SolverShiftItem(
                    id=s.id,
                    name=s.name,
                    start_time=s.start_time.strftime("%H:%M:%S"),
                    end_time=s.end_time.strftime("%H:%M:%S"),
                    applicable_days=app_days,
                )
            )

        role_items: List[SolverRoleItem] = [
            SolverRoleItem(id=r.id, name=r.name) for r in roles
        ]

        emp_items: List[SolverEmployeeItem] = []
        for e in employees:
            wt = serialized_wt.get(str(e.id), {})
            worked_h = float(wt.get("worked_or_scheduled_hours", 0.0))
            rem_h = float(
                wt.get(
                    "remaining_monthly_target",
                    max(0.0, float(e.target_hours_per_month) - worked_h)
                    if e.target_hours_per_month is not None
                    else 0.0,
                )
            )
            eff_h = float(wt.get("effective_weekly_target_hours", rem_h))
            eff_min = int(wt.get("effective_weekly_target_minutes", int(round(eff_h * 60))))
            scarcity = float(wt.get("scarcity_ratio", 0.0))
            emp_items.append(
                SolverEmployeeItem(
                    id=str(e.id),
                    full_name=e.full_name,
                    role_ids=[ur.id for ur in getattr(e, "job_roles", [])],
                    target_hours_per_month=float(e.target_hours_per_month)
                    if e.target_hours_per_month is not None
                    else None,
                    target_shifts_per_month=e.target_shifts_per_month,
                    worked_or_scheduled_hours=worked_h,
                    remaining_monthly_target=rem_h,
                    effective_weekly_target_hours=eff_h,
                    effective_weekly_target_minutes=eff_min,
                    scarcity_ratio=scarcity,
                )
            )

        return SolverJobPayload(
            job_id=job_id or str(uuid4()),
            tenant_id=tid,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            save=save,
            shifts=shift_items,
            roles=role_items,
            employees=emp_items,
            requirements=req_items,
            availabilities=avail_items,
            leave_days=leave_items,
            weekly_targets=serialized_wt,
        )

    def finalize_solver_result(
        self,
        raw_result: Dict[str, Any],
        start_date: date,
        end_date: date,
        save: bool = False,
        actor: Any = None,
    ) -> Dict[str, Any]:
        """
        Przetwarza wynik JSON zwrócony przez `solve_from_payload` (lub z kolejki RabbitMQ `wfm.solver.results`):
        - emituje zdarzenia biznesowe `log_event` (SOLVER / DEFICIT),
        - opcjonalnie zapisuje wygenerowane wpisy `Schedule` w bazie (gdy `save=True`),
        - hydratuje typy (`UUID`, `date`, `time`) w liście `schedules`.
        """
        from .solver import _parse_time_str

        tid = self.tenant_id
        status_str = raw_result.get("status", "infeasible")
        explanation = raw_result.get("solver_explanation", {})
        status_name = explanation.get("solver_status", status_str.upper())
        solve_duration = float(explanation.get("solve_duration_sec", 0.0))
        warnings = raw_result.get("warnings", [])

        if status_str == "success":
            deficit_details = explanation.get("deficit_details", {})
            employee_summary_log = explanation.get("employee_summary_log", {})

            if warnings:
                log_event(
                    "DEFICIT",
                    f"Wykryto braki kadrowe przy generowaniu grafiku ({len(warnings)} pozycji)",
                    deficit_details,
                    level="WARNING",
                    actor=actor or "System / Solver",
                    tenant_id=tid,
                )

            raw_schedules = raw_result.get("schedules", [])
            log_event(
                "SOLVER",
                f"Wygenerowano grafik pracy ({start_date} – {end_date})",
                {
                    "zakres": f"{start_date} - {end_date}",
                    "status": status_name,
                    "czas_wykonania_s": round(solve_duration, 2),
                    "przypisane_zmiany": len(raw_schedules),
                    "liczba_deficytow": len(warnings),
                    "pracownicy": employee_summary_log,
                },
                level="INFO" if not warnings else "WARNING",
                actor=actor or "System / Solver",
                tenant_id=tid,
            )

            enriched_schedules: List[Dict[str, Any]] = []
            if save:
                from ..models import ShiftAuditLog

                statements = select(Schedule).where(
                    Schedule.date >= start_date, Schedule.date <= end_date
                )
                results = self.session.exec(statements).all()
                res_ids = [r.id for r in results]
                if res_ids:
                    for al in self.session.exec(
                        select(ShiftAuditLog).where(ShiftAuditLog.schedule_id.in_(res_ids))
                    ).all():
                        al.schedule_id = None
                        self.session.add(al)
                for res in results:
                    self.session.delete(res)

                persisted_rows: List[ Tuple[Schedule, Dict[str, Any]] ] = []
                for item in raw_schedules:
                    d_val = (
                        date.fromisoformat(item["date"])
                        if isinstance(item["date"], str)
                        else item["date"]
                    )
                    u_val = (
                        UUID(str(item["user_id"]))
                        if not isinstance(item["user_id"], UUID)
                        else item["user_id"]
                    )
                    sc = Schedule(
                        date=d_val,
                        shift_def_id=int(item["shift_def_id"]),
                        user_id=u_val,
                        role_id=int(item["role_id"]),
                        is_published=bool(item.get("is_published", False)),
                    )
                    self.session.add(sc)
                    persisted_rows.append((sc, item))

                self.session.commit()
                logger.info(
                    f"[SOLVER WORKER] Zapisano do bazy {len(persisted_rows)} wpisów grafiku dla zakresu {start_date} - {end_date} [tenant:{tid}]."
                )

                for sc, item in persisted_rows:
                    enriched_schedules.append({
                        "id": sc.id,
                        "date": sc.date,
                        "shift_def_id": sc.shift_def_id,
                        "user_id": sc.user_id,
                        "role_id": sc.role_id,
                        "is_published": sc.is_published,
                        "user_name": item.get("user_name", "Unknown"),
                        "role_name": item.get("role_name", "Unknown"),
                        "shift_name": item.get("shift_name", "Unknown"),
                        "start_time": _parse_time_str(item["start_time"])
                        if item.get("start_time")
                        else None,
                        "end_time": _parse_time_str(item["end_time"])
                        if item.get("end_time")
                        else None,
                    })
            else:
                for item in raw_schedules:
                    d_val = (
                        date.fromisoformat(item["date"])
                        if isinstance(item["date"], str)
                        else item["date"]
                    )
                    u_val = (
                        UUID(str(item["user_id"]))
                        if not isinstance(item["user_id"], UUID)
                        else item["user_id"]
                    )
                    id_val = (
                        UUID(str(item["id"]))
                        if item.get("id") and not isinstance(item["id"], UUID)
                        else item.get("id")
                    )
                    enriched_schedules.append({
                        "id": id_val,
                        "date": d_val,
                        "shift_def_id": int(item["shift_def_id"]),
                        "user_id": u_val,
                        "role_id": int(item["role_id"]),
                        "is_published": bool(item.get("is_published", False)),
                        "user_name": item.get("user_name", "Unknown"),
                        "role_name": item.get("role_name", "Unknown"),
                        "shift_name": item.get("shift_name", "Unknown"),
                        "start_time": _parse_time_str(item["start_time"])
                        if item.get("start_time")
                        else None,
                        "end_time": _parse_time_str(item["end_time"])
                        if item.get("end_time")
                        else None,
                    })

            clean_explanation = {
                k: v
                for k, v in explanation.items()
                if k not in ("deficit_details", "employee_summary_log")
            }
            return {
                "status": "success",
                "count": len(enriched_schedules),
                "schedules": enriched_schedules,
                "warnings": warnings,
                "weekly_targets": raw_result.get("weekly_targets", {}),
                "solver_explanation": clean_explanation,
            }
        else:
            log_event(
                "SOLVER",
                f"Solver nie znalazł dopuszczalnego grafiku ({start_date} – {end_date})",
                {
                    "zakres": f"{start_date} - {end_date}",
                    "status": status_name,
                    "czas_wykonania_s": round(solve_duration, 2),
                    "przypisane_zmiany": 0,
                    "liczba_deficytow": 0,
                },
                level="ERROR",
                actor=actor or "System / Solver",
                tenant_id=tid,
            )
            clean_explanation = {
                k: v
                for k, v in explanation.items()
                if k not in ("deficit_details", "employee_summary_log")
            }
            return {
                "status": "infeasible",
                "count": 0,
                "warnings": [],
                "weekly_targets": raw_result.get("weekly_targets", {}),
                "solver_explanation": clean_explanation,
            }

