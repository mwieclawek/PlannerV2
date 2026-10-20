from typing import List, Optional
from datetime import date
from uuid import UUID
from sqlmodel import Session, select
from ..models import Availability, Schedule, ShiftDefinition, JobRole
from ..schemas import AvailabilityUpdate
import logging

logger = logging.getLogger(__name__)

class EmployeeService:
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

    def get_availability(self, user_id: UUID, start_date: date, end_date: date) -> List[Availability]:
        statement = select(Availability).where(
            Availability.user_id == user_id,
            Availability.date >= start_date,
            Availability.date <= end_date
        )
        return self.session.exec(statement).all()

    def update_availability(self, user_id: UUID, updates: List[AvailabilityUpdate]):
        for up in updates:
            existing = self.session.exec(select(Availability).where(
                Availability.user_id == user_id,
                Availability.date == up.date,
                Availability.shift_def_id == up.shift_def_id
            )).first()
            
            if existing:
                existing.status = up.status
                self.session.add(existing)
            else:
                new_avail = Availability(
                    user_id=user_id,
                    date=up.date,
                    shift_def_id=up.shift_def_id,
                    status=up.status
                )
                self.session.add(new_avail)
        
        self.session.commit()
        logger.info(f"Updated availability for user {user_id}: {len(updates)} records changed.")

    def link_google_calendar(self, user_id: UUID, auth_code: str):
        import os
        import httpx
        from fastapi import HTTPException
        from ..models import User

        user = self.session.get(User, user_id)
        if not user or (self.tenant_id is not None and user.tenant_id != self.tenant_id):
            raise HTTPException(status_code=404, detail="User not found")

        # 1. If auth_code is already an access token (from Flutter Web GoogleSignIn, starts with ya29.)
        if auth_code.startswith("ya29."):
            try:
                verify_res = httpx.get(
                    f"https://www.googleapis.com/oauth2/v3/tokeninfo?access_token={auth_code}",
                    timeout=10.0
                )
                if verify_res.status_code == 200:
                    user.google_access_token = auth_code
                    self.session.add(user)
                    self.session.commit()
                    logger.warning(
                        f"User {user_id} linked Google Calendar with a bare access token "
                        "(no refresh_token): sync will stop after ~1h. Client must send a serverAuthCode."
                    )
                    return
                else:
                    try:
                        err_msg = verify_res.json().get("error_description", verify_res.text)
                    except Exception:
                        err_msg = verify_res.text
                    raise HTTPException(status_code=400, detail=f"Google OAuth Error: {err_msg}")
            except httpx.RequestError as e:
                raise HTTPException(status_code=500, detail=f"Could not connect to Google OAuth service: {str(e)}")

        # 2. Otherwise exchange authorization code for tokens
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "postmessage")

        if not client_id or not client_secret:
            raise HTTPException(status_code=500, detail="Google Calendar OAuth is not configured on the server")

        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }

        try:
            response = httpx.post(token_url, data=data, timeout=15.0)
            if response.status_code == 400 and redirect_uri != "postmessage":
                # Web popup GIS code client always uses redirect_uri="postmessage"
                data["redirect_uri"] = "postmessage"
                response = httpx.post(token_url, data=data, timeout=15.0)
            response.raise_for_status()
            token_data = response.json()
            
            user.google_access_token = token_data.get("access_token")
            # Refresh token is returned only when the consent URL used access_type=offline
            # (+ prompt=consent). Never overwrite an existing refresh_token with None.
            if token_data.get("refresh_token"):
                user.google_refresh_token = token_data.get("refresh_token")
            elif not user.google_refresh_token:
                logger.warning(
                    f"Google did not return a refresh_token for user {user_id}; "
                    "calendar sync will stop when the access token expires."
                )
            self.session.add(user)
            self.session.commit()
        except httpx.HTTPStatusError as e:
            # Check if this was an access token that didn't start with ya29.
            try:
                verify_res = httpx.get(
                    f"https://www.googleapis.com/oauth2/v3/tokeninfo?access_token={auth_code}",
                    timeout=5.0
                )
                if verify_res.status_code == 200:
                    user.google_access_token = auth_code
                    self.session.add(user)
                    self.session.commit()
                    return
            except Exception:
                pass

            try:
                error_detail = e.response.json().get("error_description", "Failed to link Google Calendar")
            except Exception:
                error_detail = e.response.text
            raise HTTPException(status_code=400, detail=f"Google OAuth Error: {error_detail}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Could not connect to Google OAuth service: {str(e)}")

    def get_google_calendar_status(self, user_id: UUID) -> dict:
        from ..models import User
        from .google_calendar_service import GoogleCalendarService
        user = self.session.get(User, user_id)
        if not user:
            return {"connected": False}
        if not (user.google_refresh_token or user.google_access_token):
            return {"connected": False}

        cal_service = GoogleCalendarService(self.session)
        token = cal_service.get_valid_access_token(user)
        if not token:
            return {
                "connected": False,
                "needs_reauth": True,
                "message": "Połączenie z Kalendarzem Google wygasło. Połącz ponownie."
            }
        return {"connected": True}

    def unlink_google_calendar(self, user_id: UUID):
        from ..models import User
        from fastapi import HTTPException
        user = self.session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.google_access_token = None
        user.google_refresh_token = None
        self.session.add(user)
        self.session.commit()

    def get_schedule(self, user_id: UUID, start_date: date, end_date: date) -> List[dict]:
        statement = select(Schedule).where(
            Schedule.user_id == user_id,
            Schedule.date >= start_date,
            Schedule.date <= end_date,
            Schedule.is_published == True 
        )
        schedules = self.session.exec(statement).all()
        
        from ..models import ShiftGiveaway, GiveawayStatus, User
        giveaways = self.session.exec(
            select(ShiftGiveaway.schedule_id).where(
                ShiftGiveaway.status == GiveawayStatus.OPEN
            )
        ).all()
        giveaway_ids = set(str(g) for g in giveaways)

        # Fetch all published schedules in range (for coworker data)
        all_schedules_in_range = self.session.exec(
            select(Schedule).join(User, Schedule.user_id == User.id).where(
                Schedule.date >= start_date,
                Schedule.date <= end_date,
                Schedule.is_published == True,
                User.tenant_id == self.tenant_id
            )
        ).all()
        
        # Map: (date, shift_def_id) -> List[(user_id, role_id)]
        shift_workers_map: dict = {}
        for s in all_schedules_in_range:
            key = (s.date, s.shift_def_id)
            if key not in shift_workers_map:
                shift_workers_map[key] = []
            if s.user_id != user_id:  # exclude self
                shift_workers_map[key].append((s.user_id, s.role_id))

        # Fetch all coworker users
        all_user_ids = set(uid for entries in shift_workers_map.values() for uid, _ in entries)
        users_map: dict = {}
        if all_user_ids:
            users = self.session.exec(
                select(User).where(User.id.in_(all_user_ids), User.tenant_id == self.tenant_id)
            ).all()
            users_map = {u.id: u.full_name for u in users}

        # Fetch all role names we might need
        all_role_ids = set(rid for entries in shift_workers_map.values() for _, rid in entries)
        roles_map: dict = {}
        if all_role_ids:
            roles = self.session.exec(select(JobRole).where(JobRole.id.in_(all_role_ids))).all()
            roles_map = {r.id: r.name for r in roles}

        response = []
        for s in schedules:
            shift = self.session.get(ShiftDefinition, s.shift_def_id)
            
            coworker_entries = shift_workers_map.get((s.date, s.shift_def_id), [])
            coworkers = [
                {
                    "name": users_map.get(uid, "Unknown"),
                    "role_name": roles_map.get(rid, "Unknown"),
                }
                for uid, rid in coworker_entries
            ]
            
            response.append({
                "id": s.id,
                "date": s.date,
                "shift_name": shift.name if shift else "Unknown",
                "role_name": self.session.get(JobRole, s.role_id).name if s.role_id else "Unknown",
                "start_time": shift.start_time.strftime("%H:%M") if shift and shift.start_time else "",
                "end_time": shift.end_time.strftime("%H:%M") if shift and shift.end_time else "",
                "is_on_giveaway": str(s.id) in giveaway_ids,
                "coworkers": coworkers,
                "role_id": s.role_id,
                "shift_def_id": s.shift_def_id,
            })
        return response

    def get_team_schedule(self, start_date: date, end_date: date) -> List[dict]:
        from ..models import JobRole, ShiftDefinition, User, ShiftGiveaway, GiveawayStatus
        
        statement = select(Schedule).join(User, Schedule.user_id == User.id).where(
            Schedule.date >= start_date,
            Schedule.date <= end_date,
            Schedule.is_published == True,
            User.tenant_id == self.tenant_id
        ).order_by(Schedule.date)
        schedules = self.session.exec(statement).all()
        
        giveaways = self.session.exec(
            select(ShiftGiveaway.schedule_id).where(
                ShiftGiveaway.status == GiveawayStatus.OPEN
            )
        ).all()
        giveaway_ids = set(str(g) for g in giveaways)

        response = []
        for s in schedules:
            shift = self.session.get(ShiftDefinition, s.shift_def_id)
            user = self.session.get(User, s.user_id)
            role = self.session.get(JobRole, s.role_id)
            
            if not user or not shift:
                continue

            response.append({
                "id": s.id,
                "date": s.date,
                "shift_def_id": s.shift_def_id,
                "user_id": s.user_id,
                "role_id": s.role_id,
                "is_published": s.is_published,
                "user_name": user.full_name,
                "role_name": role.name if role else "Unknown",
                "shift_name": shift.name,
                "start_time": shift.start_time,
                "end_time": shift.end_time,
                "is_on_giveaway": str(s.id) in giveaway_ids,
            })
        return response

    # ═══════════════════════════════════════════════════════════════════════════
    #  AttendanceConfig & Attendance Registration Enforcement
    # ═══════════════════════════════════════════════════════════════════════════

    def get_missing_attendance(
        self,
        current_user,
        background_tasks=None,
    ) -> dict:
        from datetime import datetime, timedelta
        from fastapi import HTTPException
        from ..models import Attendance, Notification, RestaurantConfig
        from .push_service import PushService, send_push_to_tokens

        if current_user.tenant_id != self.tenant_id:
            raise HTTPException(status_code=403, detail="Brak dostępu do zasobów innej restauracji")

        config = self.session.get(RestaurantConfig, self.tenant_id)
        if not config or not getattr(config, "require_attendance_registration", False):
            return {
                "require_attendance_registration": False,
                "attendance_required_from": None,
                "missing": [],
            }

        today = date.today()
        now_dt = datetime.now()
        cutoff_start = getattr(config, "attendance_required_from", None) or (today - timedelta(days=30))
        if cutoff_start < today - timedelta(days=60):
            cutoff_start = today - timedelta(days=60)

        if cutoff_start > today:
            return {
                "require_attendance_registration": True,
                "attendance_required_from": cutoff_start.isoformat(),
                "missing": [],
            }

        schedules = self.session.exec(
            select(Schedule).where(
                Schedule.user_id == current_user.id,
                Schedule.date >= cutoff_start,
                Schedule.date <= today,
                Schedule.is_published == True,
            ).order_by(Schedule.date.desc())
        ).all()

        existing_att = self.session.exec(
            select(Attendance.date).where(
                Attendance.user_id == current_user.id,
                Attendance.date >= cutoff_start,
                Attendance.date <= today,
            )
        ).all()
        registered_dates = set(existing_att)

        missing = []
        push_svc = PushService(self.session)
        commit_needed = False

        for sch in schedules:
            if sch.date in registered_dates:
                continue
            shift = self.session.get(ShiftDefinition, sch.shift_def_id)
            if not shift:
                continue

            start_dt = datetime.combine(sch.date, shift.start_time)
            end_dt = datetime.combine(sch.date, shift.end_time)
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)

            if now_dt < end_dt + timedelta(minutes=30):
                continue

            role = self.session.get(JobRole, sch.role_id) if sch.role_id else None
            missing.append({
                "schedule_id": str(sch.id),
                "date": sch.date.isoformat(),
                "shift_name": shift.name,
                "role_name": role.name if role else None,
                "start_time": shift.start_time.strftime("%H:%M"),
                "end_time": shift.end_time.strftime("%H:%M"),
            })

            notif_title = f"Brak rejestracji obecności ({sch.date.isoformat()})"
            already_notified = self.session.exec(
                select(Notification).where(
                    Notification.user_id == current_user.id,
                    Notification.title == notif_title,
                )
            ).first()
            if not already_notified:
                notif_body = (
                    f"Minęło 30 minut od zakończenia Twojej zmiany '{shift.name}' "
                    f"({shift.start_time.strftime('%H:%M')} - {shift.end_time.strftime('%H:%M')}) "
                    f"w dniu {sch.date.isoformat()}. Prosimy o zarejestrowanie obecności lub zgłoszenie nieobecności."
                )
                self.session.add(
                    Notification(
                        user_id=current_user.id,
                        title=notif_title,
                        body=notif_body,
                    )
                )
                commit_needed = True
                tokens = push_svc._get_user_tokens(current_user.id)
                if tokens and background_tasks is not None:
                    background_tasks.add_task(send_push_to_tokens, tokens, notif_title, notif_body)

        if commit_needed:
            self.session.commit()

        return {
            "require_attendance_registration": True,
            "attendance_required_from": (
                config.attendance_required_from.isoformat()
                if getattr(config, "attendance_required_from", None)
                else None
            ),
            "missing": missing,
        }

    def get_attendance_defaults(self, current_user, target_date: date) -> dict:
        from fastapi import HTTPException

        if current_user.tenant_id != self.tenant_id:
            raise HTTPException(status_code=403, detail="Brak dostępu do zasobów innej restauracji")

        schedule = self.session.exec(
            select(Schedule).where(
                Schedule.user_id == current_user.id,
                Schedule.date == target_date,
            )
        ).first()

        if schedule:
            shift = self.session.get(ShiftDefinition, schedule.shift_def_id)
            return {
                "scheduled": True,
                "check_in": shift.start_time.strftime("%H:%M") if shift else None,
                "check_out": shift.end_time.strftime("%H:%M") if shift else None,
                "shift_name": shift.name if shift else None,
            }
        return {"scheduled": False, "check_in": None, "check_out": None, "shift_name": None}

    def register_attendance(
        self,
        current_user,
        target_date: date,
        check_in: str = "00:00",
        check_out: str = "00:00",
        checklist_skip_reason: Optional[str] = None,
        is_absent: bool = False,
        absence_reason: Optional[str] = None,
    ) -> dict:
        from datetime import datetime, time, timedelta
        from fastapi import HTTPException
        from ..models import Attendance, AttendanceStatus, RestaurantConfig
        from .operations_service import OperationsService

        if current_user.tenant_id != self.tenant_id:
            raise HTTPException(status_code=403, detail="Brak dostępu do zasobów innej restauracji")

        today = date.today()
        # 1. Block premature / future-date attendance registration
        if target_date > today:
            raise HTTPException(
                status_code=400,
                detail="Nie można rejestrować obecności dla przyszłych dat (przedwczesne odbicie).",
            )
        if target_date < today - timedelta(days=60):
            raise HTTPException(
                status_code=400,
                detail="Nie można rejestrować obecności starszej niż 60 dni.",
            )

        # 2. Check if already registered for this date
        existing = self.session.exec(
            select(Attendance).where(
                Attendance.user_id == current_user.id,
                Attendance.date == target_date,
            )
        ).first()
        if existing:
            return {"error": "Attendance already registered for this date"}

        # 3. Check if employee was scheduled on target_date
        schedule = self.session.exec(
            select(Schedule).where(
                Schedule.user_id == current_user.id,
                Schedule.date == target_date,
            )
        ).first()
        was_scheduled = schedule is not None

        if is_absent:
            if not was_scheduled:
                raise HTTPException(
                    status_code=400,
                    detail="Nie można zgłosić nieobecności w dniu bez zaplanowanej zmiany w grafiku.",
                )
            if not absence_reason or not absence_reason.strip():
                raise HTTPException(status_code=400, detail="Podaj powód nieobecności")
            in_time = time(0, 0)
            out_time = time(0, 0)
            status = AttendanceStatus.CONFIRMED
        else:
            try:
                in_time = datetime.strptime(check_in.strip(), "%H:%M").time()
                out_time = datetime.strptime(check_out.strip(), "%H:%M").time()
            except (ValueError, AttributeError):
                raise HTTPException(
                    status_code=400,
                    detail="Nieprawidłowy format godzin wejścia/wyjścia (wymagany HH:MM).",
                )

            if in_time == out_time:
                raise HTTPException(
                    status_code=400,
                    detail="Godzina wyjścia musi różnić się od godziny wejścia.",
                )

            # Enforce mandatory checklists on clock-out
            ops = OperationsService(self.session, self.tenant_id)
            validation = ops.validate_clockout_checklists(current_user, target_date)
            if not validation["all_mandatory_completed"] and (
                not checklist_skip_reason or not checklist_skip_reason.strip()
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Niewykonane obowiązkowe zadania z checklisty zamknięcia. Podaj powód pominięcia (checklist_skip_reason).",
                )

            status = AttendanceStatus.CONFIRMED if was_scheduled else AttendanceStatus.PENDING

        attendance = Attendance(
            user_id=current_user.id,
            date=target_date,
            check_in=in_time,
            check_out=out_time,
            was_scheduled=was_scheduled,
            status=status,
            schedule_id=schedule.id if schedule else None,
            checklist_skip_reason=checklist_skip_reason.strip() if checklist_skip_reason else None,
            is_absent=is_absent,
            absence_reason=absence_reason.strip() if (is_absent and absence_reason) else None,
        )
        self.session.add(attendance)
        self.session.commit()
        self.session.refresh(attendance)

        return {
            "id": str(attendance.id),
            "status": status.value,
            "was_scheduled": was_scheduled,
            "requires_approval": (not was_scheduled) and (not is_absent),
            "checklist_skip_reason": attendance.checklist_skip_reason,
            "is_absent": attendance.is_absent,
            "absence_reason": attendance.absence_reason,
        }

    def get_my_attendance(self, current_user, start_date: date, end_date: date) -> List[dict]:
        from fastapi import HTTPException
        from ..models import Attendance

        if current_user.tenant_id != self.tenant_id:
            raise HTTPException(status_code=403, detail="Brak dostępu do zasobów innej restauracji")

        attendances = self.session.exec(
            select(Attendance).where(
                Attendance.user_id == current_user.id,
                Attendance.date >= start_date,
                Attendance.date <= end_date,
            )
        ).all()

        return [
            {
                "id": str(a.id),
                "date": a.date.isoformat(),
                "check_in": a.check_in.strftime("%H:%M"),
                "check_out": a.check_out.strftime("%H:%M"),
                "was_scheduled": a.was_scheduled,
                "status": a.status.value,
                "checklist_skip_reason": a.checklist_skip_reason,
                "is_absent": bool(a.is_absent),
                "absence_reason": a.absence_reason,
            }
            for a in attendances
        ]


