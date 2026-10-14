import os
import uuid
import logging
from contextlib import contextmanager
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any, Iterable
from urllib.parse import urlencode
import httpx
from sqlmodel import Session, select

from ..models import User, Schedule, ShiftDefinition, JobRole, RestaurantConfig

logger = logging.getLogger(__name__)

# Timezone for Polish operations. tzdata is required on platforms without a system
# tz database (e.g. Windows / slim containers) - a fixed offset would be wrong in winter.
try:
    import zoneinfo
    WARSAW_TZ = zoneinfo.ZoneInfo("Europe/Warsaw")
except Exception:
    from datetime import timezone
    logger.error(
        "zoneinfo 'Europe/Warsaw' unavailable (install the 'tzdata' package). "
        "Falling back to fixed UTC+2 - calendar events will be off by 1h in winter."
    )
    WARSAW_TZ = timezone(timedelta(hours=2))

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"
CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


def build_authorization_url(state: Optional[str] = None) -> str:
    """
    Builds the Google OAuth2 consent URL.

    `access_type=offline` + `prompt=consent` make Google ALWAYS return a refresh_token.
    Without them the access token (valid ~1h) cannot be renewed and background sync
    silently stops working after an hour.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise ValueError("GOOGLE_CLIENT_ID is not configured")
    params = {
        "client_id": client_id,
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI", "postmessage"),
        "response_type": "code",
        "scope": GOOGLE_CALENDAR_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    if state:
        params["state"] = state
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def compute_event_window(day: date, start: time, end: time):
    """
    Returns timezone-aware (start_dt, end_dt) in Europe/Warsaw.
    Shifts where end <= start cross midnight and end on the following day.
    """
    start_dt = datetime.combine(day, start).replace(tzinfo=WARSAW_TZ)
    end_dt = datetime.combine(day, end).replace(tzinfo=WARSAW_TZ)
    if end <= start:
        end_dt += timedelta(days=1)
    return start_dt, end_dt


class GoogleCalendarService:
    def __init__(self, session: Session):
        self.session = session

    def get_valid_access_token(self, user: User, force_refresh: bool = False) -> Optional[str]:
        """
        Retrieves a valid Google access token for the user.
        If the access token is expired (or `force_refresh` is set) and a refresh token
        is present, it automatically refreshes the token against Google OAuth.
        """
        token = user.google_access_token

        # Verify token validity
        if token and not force_refresh:
            try:
                res = httpx.get(
                    f"https://www.googleapis.com/oauth2/v3/tokeninfo?access_token={token}",
                    timeout=5.0
                )
                if res.status_code == 200:
                    return token
            except Exception:
                logger.exception(f"Error checking token validity for user {user.id}")

        # If token is invalid/missing and we have a refresh token, refresh it
        refresh_token = user.google_refresh_token
        if not refresh_token:
            logger.error(
                f"User {user.id}: Google access token expired and NO refresh token stored. "
                "The user must re-link Google Calendar (consent with access_type=offline)."
            )
            return None

        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        if not client_id or not client_secret:
            logger.error("GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not configured.")
            return None

        try:
            refresh_res = httpx.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                },
                timeout=10.0
            )
            if refresh_res.status_code == 200:
                data = refresh_res.json()
                new_token = data.get("access_token")
                if new_token:
                    user.google_access_token = new_token
                    self.session.add(user)
                    self.session.commit()
                    logger.info(f"Successfully refreshed Google access token for user {user.id}")
                    return new_token
                logger.error(f"Google token refresh for user {user.id} returned no access_token")
            else:
                logger.error(
                    f"Failed to refresh Google token for user {user.id}: "
                    f"{refresh_res.status_code} {refresh_res.text}"
                )
        except Exception:
            logger.exception(f"Exception refreshing Google token for user {user.id}")

        return None

    def _build_event(self, user: User, schedule: Schedule, shift: ShiftDefinition) -> Dict[str, Any]:
        # Role is a plain FK on Schedule (JobRole); ShiftRoleLink only restricts which roles
        # may work a shift definition and is not needed to render the event.
        role = self.session.get(JobRole, schedule.role_id) if schedule.role_id else None
        role_name = role.name if role else "Pracownik"

        start_dt, end_dt = compute_event_window(schedule.date, shift.start_time, shift.end_time)

        config = None
        if getattr(user, "tenant_id", None):
            config = self.session.get(RestaurantConfig, user.tenant_id)
        if not config:
            config = self.session.exec(select(RestaurantConfig)).first()
        restaurant_name = config.name.strip() if (config and config.name and config.name.strip()) else "RestoPlan"

        return {
            "id": f"plannerv2{schedule.id.hex}",
            "summary": f"Zmiana {restaurant_name}",
            "description": (
                f"Grafik pracy: {restaurant_name}\n"
                f"Stanowisko: {role_name}\n"
                f"Zmiana: {shift.name}\n"
                f"Godziny: {shift.start_time.strftime('%H:%M')} - {shift.end_time.strftime('%H:%M')}"
            ),
            # RFC3339 with explicit offset + IANA zone
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Europe/Warsaw"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "Europe/Warsaw"},
            "reminders": {"useDefault": True},
        }

    def sync_schedule_to_calendar(self, user: User, schedule: Schedule) -> bool:
        """
        Upserts a single schedule entry into Google Calendar using a deterministic event ID.
        """
        if not schedule.is_published:
            return False

        token = self.get_valid_access_token(user)
        if not token:
            logger.error(f"Cannot sync schedule {schedule.id}: no valid Google token for user {user.id}")
            return False

        shift = self.session.get(ShiftDefinition, schedule.shift_def_id)
        if not shift:
            logger.error(f"Cannot sync schedule {schedule.id}: shift definition {schedule.shift_def_id} not found")
            return False

        event_body = self._build_event(user, schedule, shift)
        event_id = event_body["id"]
        update_url = f"{CALENDAR_EVENTS_URL}/{event_id}"

        def _attempt(access_token: str) -> httpx.Response:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            # First attempt: insert new event with custom deterministic ID
            res = httpx.post(CALENDAR_EVENTS_URL, headers=headers, json=event_body, timeout=10.0)
            if res.status_code == 409:
                # Event already exists (or was cancelled): update it
                body = dict(event_body, status="confirmed")
                res = httpx.put(update_url, headers=headers, json=body, timeout=10.0)
            return res

        try:
            res = _attempt(token)
            if res.status_code == 401:
                logger.warning(f"Google returned 401 for user {user.id}; forcing token refresh and retrying")
                new_token = self.get_valid_access_token(user, force_refresh=True)
                if not new_token:
                    return False
                res = _attempt(new_token)

            if res.status_code in (200, 201):
                logger.info(f"Synced shift {schedule.id} ({schedule.date}) to Google Calendar for {user.username}")
                return True
            logger.error(
                f"Google Calendar API error {res.status_code} syncing shift {schedule.id} "
                f"for user {user.id}: {res.text}"
            )
            return False
        except Exception:
            logger.exception(f"Exception syncing shift {schedule.id} to Google Calendar")
            return False

    def delete_calendar_event(self, user: User, schedule_id: uuid.UUID) -> bool:
        """
        Deletes a schedule event from Google Calendar by its deterministic event ID.
        """
        token = self.get_valid_access_token(user)
        if not token:
            logger.error(f"Cannot delete event for schedule {schedule_id}: no valid Google token for user {user.id}")
            return False

        event_id = f"plannerv2{schedule_id.hex}"
        url = f"{CALENDAR_EVENTS_URL}/{event_id}"

        try:
            res = httpx.delete(url, headers={"Authorization": f"Bearer {token}"}, timeout=10.0)
            if res.status_code == 401:
                new_token = self.get_valid_access_token(user, force_refresh=True)
                if not new_token:
                    return False
                res = httpx.delete(url, headers={"Authorization": f"Bearer {new_token}"}, timeout=10.0)
            if res.status_code in (200, 204, 404, 410):
                logger.info(f"Deleted calendar event {event_id} for user {user.username}")
                return True
            logger.error(f"Google Calendar DELETE error {res.status_code} for event {event_id}: {res.text}")
            return False
        except Exception:
            logger.exception(f"Exception deleting calendar event {event_id}")
            return False

    def sync_user_schedules(
        self,
        user_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Syncs all published schedules for a user within the specified date range.
        Default range: from 7 days ago to 45 days in the future.
        If `tenant_id` is given the user must belong to that tenant.
        """
        user = self.session.get(User, user_id)
        if not user or (tenant_id is not None and user.tenant_id != tenant_id):
            return {"status": "error", "message": "User not found", "synced": 0, "total": 0}

        if not user.google_access_token and not user.google_refresh_token:
            return {"status": "skipped", "message": "Google Calendar not connected", "synced": 0, "total": 0}

        today = date.today()
        start = start_date or (today - timedelta(days=7))
        end = end_date or (today + timedelta(days=45))

        statement = select(Schedule).where(
            Schedule.user_id == user_id,
            Schedule.date >= start,
            Schedule.date <= end,
            Schedule.is_published == True
        )
        schedules = self.session.exec(statement).all()

        synced_count = 0
        for sched in schedules:
            if self.sync_schedule_to_calendar(user, sched):
                synced_count += 1

        return {
            "status": "success",
            "synced": synced_count,
            "total": len(schedules),
            "start_date": str(start),
            "end_date": str(end)
        }


# ── Background workers ─────────────────────────────────────────────────────────
#
# These run AFTER the HTTP response is sent (FastAPI BackgroundTasks), when the
# request-scoped session from `Depends(get_session)` is already closed and the
# tenant ContextVar must not be relied upon. They therefore accept ONLY primitive
# IDs, open their own independent DB session and filter explicitly by tenant.

@contextmanager
def background_session():
    """Independent DB session for background workers (patched in tests)."""
    from .. import database
    with Session(database.engine) as session:
        yield session


def _load_tenant_user(session: Session, user_id: uuid.UUID, restaurant_id: int) -> Optional[User]:
    user = session.exec(
        select(User).where(User.id == user_id, User.tenant_id == restaurant_id)
    ).first()
    if not user:
        logger.error(f"Calendar sync: user {user_id} not found in tenant {restaurant_id}")
    return user


def _set_tenant(restaurant_id: int) -> None:
    from ..tenant_context import set_current_tenant_id
    set_current_tenant_id(restaurant_id)


def sync_schedule_task(schedule_id: uuid.UUID, user_id: uuid.UUID, restaurant_id: int) -> None:
    """Insert/update the Google event of one schedule entry for `user_id`."""
    try:
        _set_tenant(restaurant_id)
        with background_session() as session:
            user = _load_tenant_user(session, user_id, restaurant_id)
            if not user or not (user.google_access_token or user.google_refresh_token):
                return
            schedule = session.exec(
                select(Schedule).where(Schedule.id == schedule_id, Schedule.user_id == user_id)
            ).first()
            if not schedule:
                logger.error(f"Calendar sync: schedule {schedule_id} not found for user {user_id}")
                return
            GoogleCalendarService(session).sync_schedule_to_calendar(user, schedule)
    except Exception:
        logger.exception(f"Background calendar sync failed for schedule {schedule_id}")


def delete_event_task(schedule_id: uuid.UUID, user_id: uuid.UUID, restaurant_id: int) -> None:
    """Remove the Google event of a schedule entry (schedule may already be deleted)."""
    try:
        _set_tenant(restaurant_id)
        with background_session() as session:
            user = _load_tenant_user(session, user_id, restaurant_id)
            if not user or not (user.google_access_token or user.google_refresh_token):
                return
            GoogleCalendarService(session).delete_calendar_event(user, schedule_id)
    except Exception:
        logger.exception(f"Background calendar delete failed for schedule {schedule_id}")


def sync_user_range_task(
    user_id: uuid.UUID,
    restaurant_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> None:
    """Sync all published schedules of a user within a date range."""
    try:
        _set_tenant(restaurant_id)
        with background_session() as session:
            GoogleCalendarService(session).sync_user_schedules(
                user_id, start_date=start_date, end_date=end_date, tenant_id=restaurant_id
            )
    except Exception:
        logger.exception(f"Background calendar range sync failed for user {user_id}")


def reassign_event_task(
    schedule_id: uuid.UUID,
    old_user_id: Optional[uuid.UUID],
    new_user_id: uuid.UUID,
    restaurant_id: int,
) -> None:
    """Giveaway hand-over: delete the event of the giver, create it for the taker."""
    if old_user_id:
        delete_event_task(schedule_id, old_user_id, restaurant_id)
    sync_schedule_task(schedule_id, new_user_id, restaurant_id)


def resync_shift_definition_task(shift_def_id: int, restaurant_id: int) -> None:
    """Shift hours changed: refresh every upcoming published event that uses this definition."""
    try:
        _set_tenant(restaurant_id)
        with background_session() as session:
            rows = session.exec(
                select(Schedule.id, Schedule.user_id)
                .join(User, Schedule.user_id == User.id)
                .where(
                    Schedule.shift_def_id == shift_def_id,
                    Schedule.is_published == True,
                    Schedule.date >= date.today() - timedelta(days=1),
                    User.tenant_id == restaurant_id,
                )
            ).all()
        for sched_id, user_id in rows:
            sync_schedule_task(sched_id, user_id, restaurant_id)
    except Exception:
        logger.exception(f"Background resync failed for shift definition {shift_def_id}")


def enqueue(background_tasks, func, *args, **kwargs) -> None:
    """Schedule `func` on FastAPI BackgroundTasks, or run it inline when none is available."""
    if background_tasks is not None:
        background_tasks.add_task(func, *args, **kwargs)
    else:
        func(*args, **kwargs)
