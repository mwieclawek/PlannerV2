import os
import uuid
import logging
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any
import httpx
from sqlmodel import Session, select

from ..models import User, Schedule, ShiftDefinition, JobRole, RestaurantConfig

logger = logging.getLogger(__name__)

# Timezone for Polish operations
try:
    import zoneinfo
    WARSAW_TZ = zoneinfo.ZoneInfo("Europe/Warsaw")
except Exception:
    from datetime import timezone
    WARSAW_TZ = timezone(timedelta(hours=2))


class GoogleCalendarService:
    def __init__(self, session: Session):
        self.session = session

    def get_valid_access_token(self, user: User) -> Optional[str]:
        """
        Retrieves a valid Google access token for the user.
        If the access token is expired and a refresh token is present,
        it automatically refreshes the token against Google OAuth.
        """
        token = user.google_access_token
        if not token:
            return None

        # Verify token validity
        try:
            res = httpx.get(
                f"https://www.googleapis.com/oauth2/v3/tokeninfo?access_token={token}",
                timeout=5.0
            )
            if res.status_code == 200:
                return token
        except Exception as e:
            logger.warning(f"Error checking token validity for user {user.id}: {e}")

        # If token is invalid and we have a refresh token, refresh it
        refresh_token = user.google_refresh_token
        if not refresh_token:
            logger.info(f"User {user.id} Google access token expired and no refresh token available.")
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
            else:
                logger.warning(f"Failed to refresh Google token for user {user.id}: {refresh_res.text}")
        except Exception as e:
            logger.error(f"Exception refreshing Google token for user {user.id}: {e}")

        return None

    def sync_schedule_to_calendar(self, user: User, schedule: Schedule) -> bool:
        """
        Upserts a single schedule entry into Google Calendar using a deterministic event ID.
        """
        if not schedule.is_published:
            return False

        token = self.get_valid_access_token(user)
        if not token:
            return False

        shift = self.session.get(ShiftDefinition, schedule.shift_def_id)
        if not shift:
            return False

        role = self.session.get(JobRole, schedule.role_id) if schedule.role_id else None
        role_name = role.name if role else "Pracownik"

        # Calculate start and end datetimes
        start_dt = datetime.combine(schedule.date, shift.start_time).replace(tzinfo=WARSAW_TZ)
        end_dt = datetime.combine(schedule.date, shift.end_time).replace(tzinfo=WARSAW_TZ)
        if shift.end_time <= shift.start_time:
            end_dt += timedelta(days=1)

        config = self.session.get(RestaurantConfig, 1)
        restaurant_name = config.name.strip() if (config and config.name and config.name.strip()) else "RestoPlan"

        event_id = f"plannerv2{schedule.id.hex}"
        summary = f"Zmiana {restaurant_name}"
        description = (
            f"Grafik pracy: {restaurant_name}\n"
            f"Stanowisko: {role_name}\n"
            f"Zmiana: {shift.name}\n"
            f"Godziny: {shift.start_time.strftime('%H:%M')} - {shift.end_time.strftime('%H:%M')}"
        )

        event_body = {
            "id": event_id,
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "Europe/Warsaw"
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "Europe/Warsaw"
            },
            "reminders": {
                "useDefault": True
            }
        }

        try:
            url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            res = httpx.put(url, headers=headers, json=event_body, timeout=10.0)
            if res.status_code in (200, 201):
                logger.info(f"Successfully synced shift {schedule.id} ({schedule.date}) to Google Calendar for {user.username}")
                return True
            else:
                logger.warning(f"Google Calendar API error {res.status_code} for shift {schedule.id}: {res.text}")
                return False
        except Exception as e:
            logger.error(f"Exception syncing shift {schedule.id} to Google Calendar: {e}")
            return False

    def delete_calendar_event(self, user: User, schedule_id: uuid.UUID) -> bool:
        """
        Deletes a schedule event from Google Calendar by its deterministic event ID.
        """
        token = self.get_valid_access_token(user)
        if not token:
            return False

        event_id = f"plannerv2{schedule_id.hex}"
        url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            res = httpx.delete(url, headers=headers, timeout=10.0)
            if res.status_code in (200, 204, 404, 410):
                logger.info(f"Deleted calendar event {event_id} for user {user.username}")
                return True
            else:
                logger.warning(f"Google Calendar DELETE error {res.status_code}: {res.text}")
                return False
        except Exception as e:
            logger.error(f"Exception deleting calendar event {event_id}: {e}")
            return False

    def sync_user_schedules(
        self,
        user_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Syncs all published schedules for a user within the specified date range.
        Default range: from 7 days ago to 45 days in the future.
        """
        user = self.session.get(User, user_id)
        if not user:
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
