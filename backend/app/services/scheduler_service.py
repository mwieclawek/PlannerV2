from datetime import date
from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import HTTPException
from sqlmodel import Session, select
from ..models import Schedule, User, JobRole, ShiftDefinition
from ..schemas import BatchSaveRequest, ScheduleResponse
import logging

logger = logging.getLogger(__name__)

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
        
        # Handle linked Attendance records (set schedule_id to None) to avoid FK violation
        existing_ids = [e.id for e in existing]
        if existing_ids:
            from ..models import Attendance
            linked_attendances = self.session.exec(
                select(Attendance).where(Attendance.schedule_id.in_(existing_ids))
            ).all()
            for att in linked_attendances:
                att.schedule_id = None
                self.session.add(att)
            self.session.commit() # Commit updates to Attendance first
            
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

        logger.info(f"Saved batch schedule from {batch.start_date} to {batch.end_date}. Created {count} records (is_published={is_published}).")
        return count

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
        for u_id in published_user_ids:
            enqueue(background_tasks, sync_user_range_task, u_id, self.tenant_id, start_date, end_date)

        logger.info(f"Published schedules from {start_date} to {end_date}. Affected users: {len(published_user_ids)}")
        return count

    # --- Single assignment (manager) ---
    def assign(self, assign, background_tasks=None, changed_by_user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Create or update one schedule entry; every referenced object must be in this tenant."""
        self._validate_batch_refs([assign])
        from .google_calendar_service import enqueue, sync_schedule_task
        from ..models import ShiftAuditLog

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
                changed_by_user_id=changed_by_user_id,
                action="ASSIGNMENT_CHANGE",
                old_value=old_val,
                new_value=new_val
            ))
            self.session.commit()
            if existing_daily.is_published:
                enqueue(background_tasks, sync_schedule_task, existing_daily.id, existing_daily.user_id, self.tenant_id)
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
            changed_by_user_id=changed_by_user_id,
            action="ASSIGNMENT_CHANGE",
            old_value=None,
            new_value=f"user_id={assign.user_id}, role_id={assign.role_id}, shift_def_id={assign.shift_def_id}"
        ))
        self.session.commit()
        self.session.refresh(new_entry)
        # Draft entries are not pushed to calendars; sync_schedule_task is a no-op until published,
        # and publish_schedule() syncs them.
        return {"status": "created", "id": str(new_entry.id)}

    def remove_assignment(self, schedule_id: UUID, background_tasks=None, changed_by_user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Delete one schedule entry (tenant-scoped) and its Google Calendar event."""
        entry = self.session.exec(
            select(Schedule).join(User, Schedule.user_id == User.id).where(
                Schedule.id == schedule_id, User.tenant_id == self.tenant_id
            )
        ).first()
        if not entry:
            return {"status": "not_found"}

        was_published, user_id, sched_id = entry.is_published, entry.user_id, entry.id

        from ..models import Attendance, ShiftAuditLog
        self.session.add(ShiftAuditLog(
            restaurant_id=self.tenant_id,
            shift_id=str(sched_id),
            changed_by_user_id=changed_by_user_id,
            action="UNASSIGN",
            old_value=f"user_id={user_id}, role_id={entry.role_id}, shift_def_id={entry.shift_def_id}",
            new_value=None
        ))
        for att in self.session.exec(select(Attendance).where(Attendance.schedule_id == sched_id)).all():
            att.schedule_id = None
            self.session.add(att)
        self.session.delete(entry)
        self.session.commit()

        if was_published:
            from .google_calendar_service import enqueue, delete_event_task
            enqueue(background_tasks, delete_event_task, sched_id, user_id, self.tenant_id)
        return {"status": "deleted"}
