from typing import List
from datetime import date
from uuid import UUID
from sqlmodel import Session, select
from ..models import Availability, Schedule, ShiftDefinition, JobRole
from ..schemas import AvailabilityUpdate

class EmployeeService:
    def __init__(self, session: Session):
        self.session = session

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

    def link_google_calendar(self, user_id: UUID, auth_code: str):
        import os
        import httpx
        from fastapi import HTTPException
        from ..models import User

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
            response.raise_for_status()
            token_data = response.json()
            
            user = self.session.get(User, user_id)
            if user:
                user.google_access_token = token_data.get("access_token")
                # Refresh token is typically only returned on the first authorization
                if "refresh_token" in token_data:
                    user.google_refresh_token = token_data.get("refresh_token")
                self.session.add(user)
                self.session.commit()
            else:
                raise HTTPException(status_code=404, detail="User not found")
        except httpx.HTTPStatusError as e:
            try:
                error_detail = e.response.json().get("error_description", "Failed to link Google Calendar")
            except Exception:
                error_detail = e.response.text
            raise HTTPException(status_code=400, detail=f"Google OAuth Error: {error_detail}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Could not connect to Google OAuth service: {str(e)}")

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
            select(Schedule).where(
                Schedule.date >= start_date,
                Schedule.date <= end_date,
                Schedule.is_published == True
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
            users = self.session.exec(select(User).where(User.id.in_(all_user_ids))).all()
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
            })
        return response

