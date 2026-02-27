from typing import List, Optional
from uuid import UUID
from datetime import datetime, date, timedelta
from sqlmodel import Session, select
from fastapi import HTTPException
from ..models import JobRole, ShiftDefinition, StaffingRequirement, RestaurantConfig, User, UserJobRoleLink, RoleSystem, AttendanceStatus, Schedule, Attendance
from ..schemas import JobRoleCreate, ShiftDefCreate, RequirementCreate, ConfigUpdate, UserUpdate, UserCreate

class ManagerService:
    def __init__(self, session: Session):
        self.session = session

    # --- User Management ---
    def create_user(self, user_in: "UserCreate") -> User:
        # Check if username exists
        existing_user = self.session.exec(select(User).where(User.username == user_in.username)).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")
            
        # Check if email exists (if provided)
        if user_in.email:
             existing_email = self.session.exec(select(User).where(User.email == user_in.email)).first()
             if existing_email:
                 raise HTTPException(status_code=400, detail="Email already registered")

        from ..auth_utils import get_password_hash
        hashed_password = get_password_hash(user_in.password)
        hashed_pin = get_password_hash(user_in.manager_pin) if user_in.manager_pin else None
        
        user = User(
            username=user_in.username,
            email=user_in.email,
            password_hash=hashed_password,
            full_name=user_in.full_name,
            role_system=user_in.role_system,
            target_hours_per_month=user_in.target_hours_per_month,
            target_shifts_per_month=user_in.target_shifts_per_month,
            manager_pin=hashed_pin,
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user


    # --- Roles ---
    def create_role(self, role_in: JobRoleCreate) -> JobRole:
        role = JobRole(name=role_in.name, color_hex=role_in.color_hex)
        self.session.add(role)
        self.session.commit()
        self.session.refresh(role)
        return role

    def get_roles(self) -> List[JobRole]:
        return self.session.exec(select(JobRole)).all()

    def update_role(self, role_id: int, role_in: JobRoleCreate) -> JobRole:
        role = self.session.get(JobRole, role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        role.name = role_in.name
        role.color_hex = role_in.color_hex
        self.session.add(role)
        self.session.commit()
        self.session.refresh(role)
        return role

    def delete_role(self, role_id: int):
        role = self.session.get(JobRole, role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        try:
            self.session.delete(role)
            self.session.commit()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Cannot delete role: {str(e)}")

    # --- Shifts ---
    def create_shift(self, shift_in: ShiftDefCreate) -> ShiftDefinition:
        s_time = datetime.strptime(shift_in.start_time, "%H:%M").time()
        e_time = datetime.strptime(shift_in.end_time, "%H:%M").time()
        
        existing = self.session.exec(select(ShiftDefinition).where(
            ShiftDefinition.start_time == s_time,
            ShiftDefinition.end_time == e_time
        )).first()
        if existing:
            raise HTTPException(status_code=400, detail="Shift with these hours already exists")

        from ..models import ShiftDefinitionDayLink
        
        shift = ShiftDefinition(
            name=shift_in.name, 
            start_time=s_time, 
            end_time=e_time
        )
        self.session.add(shift)
        self.session.commit()
        self.session.refresh(shift)
        
        for d in shift_in.applicable_days:
            link = ShiftDefinitionDayLink(shift_def_id=shift.id, day_of_week=d)
            self.session.add(link)
            
        self.session.commit()
        self.session.refresh(shift)
        return shift

    def update_shift(self, shift_id: int, shift_in: ShiftDefCreate) -> ShiftDefinition:
        shift = self.session.get(ShiftDefinition, shift_id)
        if not shift:
             raise HTTPException(status_code=404, detail="Shift not found")
        
        s_time = datetime.strptime(shift_in.start_time, "%H:%M").time()
        e_time = datetime.strptime(shift_in.end_time, "%H:%M").time()

        existing = self.session.exec(select(ShiftDefinition).where(
            ShiftDefinition.start_time == s_time,
            ShiftDefinition.end_time == e_time,
            ShiftDefinition.id != shift_id
        )).first()
        if existing:
            raise HTTPException(status_code=400, detail="Shift with these hours already exists")

        from ..models import ShiftDefinitionDayLink
        shift.name = shift_in.name
        shift.start_time = s_time
        shift.end_time = e_time
        
        old_links = self.session.exec(select(ShiftDefinitionDayLink).where(ShiftDefinitionDayLink.shift_def_id == shift.id)).all()
        for link in old_links:
            self.session.delete(link)
            
        for d in shift_in.applicable_days:
            link = ShiftDefinitionDayLink(shift_def_id=shift.id, day_of_week=d)
            self.session.add(link)
            
        self.session.add(shift)
        self.session.commit()
        self.session.refresh(shift)
        return shift

    def delete_shift(self, shift_id: int):
        shift = self.session.get(ShiftDefinition, shift_id)
        if not shift:
            raise HTTPException(status_code=404, detail="Shift not found")
        try:
            self.session.delete(shift)
            self.session.commit()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Cannot delete shift: {str(e)}")

    # --- Requirements ---
    def set_requirements(self, reqs: List[RequirementCreate]) -> List[StaffingRequirement]:
        results = []
        
        # Determine the scope of days to clear based on the incoming request
        # If the request contains dates, clear those dates. If day_of_week, clear those days.
        dates_to_clear = set()
        days_to_clear = set()
        
        for r in reqs:
            if r.date:
                dates_to_clear.add(r.date)
            elif r.day_of_week is not None:
                days_to_clear.add(r.day_of_week)
                
        # Clear existing requirements for the affected days
        if dates_to_clear:
            old_reqs = self.session.exec(
                select(StaffingRequirement).where(StaffingRequirement.date.in_(list(dates_to_clear)))
            ).all()
            for old in old_reqs:
                self.session.delete(old)
                
        if days_to_clear:
            old_reqs = self.session.exec(
                select(StaffingRequirement).where(StaffingRequirement.day_of_week.in_(list(days_to_clear)))
            ).all()
            for old in old_reqs:
                self.session.delete(old)
        
        # If there are no requirements (e.g. everything was deleted in the UI), reqs is empty
        # but the above logic won't clear anything because dates_to_clear is empty.
        # However, the frontend sends ALL requirements for the given week/template.
        # Since the provided API doesn't know the exact "week" if reqs is empty, 
        # the clear logic above only works if there's at least one requirement left.
        # This requires the frontend to send a "clear_dates" parameter, or we accept a slightly
        # altered payload. Let's see if we can do this without changing the API signature.
        
        for r in reqs:
            new_req = StaffingRequirement(
                date=r.date,
                day_of_week=r.day_of_week,
                shift_def_id=r.shift_def_id,
                role_id=r.role_id,
                min_count=r.min_count
            )
            self.session.add(new_req)
            results.append(new_req)
                
        self.session.commit()
        for res in results:
            self.session.refresh(res)
        return results

    def get_requirements(self, start_date: date, end_date: date) -> List[StaffingRequirement]:
        specific = self.session.exec(select(StaffingRequirement).where(
            StaffingRequirement.date >= start_date,
            StaffingRequirement.date <= end_date
        )).all()
        
        global_reqs = self.session.exec(select(StaffingRequirement).where(
            StaffingRequirement.day_of_week != None
        )).all()
        
        return list(specific) + list(global_reqs)

    # --- Config ---
    def get_config(self) -> RestaurantConfig:
        config = self.session.get(RestaurantConfig, 1)
        if not config:
            return RestaurantConfig(name="My Restaurant")
        return config

    def update_config(self, update: ConfigUpdate) -> RestaurantConfig:
        config = self.session.get(RestaurantConfig, 1)
        data = update.dict(exclude_unset=True)
        opening_hours_json = data.pop("opening_hours", None)
        
        if not config:
            if "name" not in data:
                 data["name"] = "My Restaurant"
            config = RestaurantConfig(id=1, **data)
            self.session.add(config)
            self.session.commit()
            self.session.refresh(config)
        else:
            for key, value in data.items():
                if key != "opening_hours":
                    setattr(config, key, value)
            self.session.add(config)
            self.session.commit()
            
        if opening_hours_json is not None:
            import json
            from ..models import RestaurantOpeningHour
            from datetime import datetime
            
            old_hours = self.session.exec(select(RestaurantOpeningHour).where(RestaurantOpeningHour.config_id == config.id)).all()
            for h in old_hours:
                self.session.delete(h)
                
            hours_dict = json.loads(opening_hours_json)
            for day_str, times in hours_dict.items():
                day_int = int(day_str)
                open_t = datetime.strptime(times["open"], "%H:%M").time()
                close_t = datetime.strptime(times["close"], "%H:%M").time()
                new_h = RestaurantOpeningHour(
                    config_id=config.id,
                    day_of_week=day_int,
                    open_time=open_t,
                    close_time=close_t
                )
                self.session.add(new_h)
            self.session.commit()
            
        self.session.refresh(config)
        return config

    # --- User Role Management ---
    def update_user(self, user_id: UUID, update: UserUpdate) -> User:
        user = self.session.get(User, user_id)
        if not user:
             raise HTTPException(status_code=404, detail="User not found")
             
        # Use exclude_unset=False to allow explicitly passed None fields 
        # But wait, if we use exclude_unset=False we overwrite everything with None!
        # The frontend uses PATCH-like behavior but sends all fields it updates.
        # Actually pydantic v2 `model_dump(exclude_unset=True)` keeps explicitly set Nones if the field
        # is optional and unset wasn't true. BUT `update: UserUpdate` might receive nulls 
        # that are treated as set. Let's see:
        data = update.dict(exclude_unset=True)
        
        # In Pydantic, if a field is sent as null in JSON, it is "set" to None.
        # exclude_unset=True will INCLUDE it, but only if the frontend actually sent `"target_hours_per_month": null`.
        # The issue might be that the frontend is completely omitting the key when it's empty, or sending an empty string.
        # Let's add a check: if the frontend sends it as explicit null, `data` WILL have it.
        # If the frontend is completely omitting it, we can't tell if it meant "don't change" or "clear".
        # We need the frontend (api_service) to explicitly send null.
        
        # Handle first_name and last_name mapping to full_name if provided
        if "first_name" in data or "last_name" in data:
            current_first = ""
            current_last = ""
            # Try to split existing full_name
            if user.full_name:
                parts = user.full_name.split(" ", 1)
                current_first = parts[0]
                if len(parts) > 1:
                    current_last = parts[1]
            
            new_first = data.pop("first_name", current_first)
            new_last = data.pop("last_name", current_last)
            
            new_full_name = f"{new_first} {new_last}".strip()
            if new_full_name:
                data["full_name"] = new_full_name

        for key, value in data.items():
            setattr(user, key, value)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def update_user_roles(self, user_id: UUID, role_ids: List[int]):
        user = self.session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        existing_links = self.session.exec(select(UserJobRoleLink).where(UserJobRoleLink.user_id == user_id)).all()
        for link in existing_links:
            self.session.delete(link)
        
        for role_id in role_ids:
            new_link = UserJobRoleLink(user_id=user_id, role_id=role_id)
            self.session.add(new_link)
            
        self.session.commit()

    # --- New Features Logic ---

    def get_users_with_shifts(self, include_inactive: bool = False) -> List[dict]:
        """Get all users with their next upcoming shift"""
        from ..models import Schedule
        from ..schemas import NextShiftInfo
        
        query = select(User).where(User.role_system == RoleSystem.EMPLOYEE)
        if not include_inactive:
            query = query.where(User.is_active == True)
        users = self.session.exec(query).all()
        result = []
        today = date.today()
        
        # Pre-fetch all future schedules to minimize queries (optimization)
        # or just query for each user for simplicity first. 
        # Given the scale, query per user is fine for now but let's try to be efficient.
        
        for user in users:
            # Find next shift >= today
            next_shift = self.session.exec(
                select(Schedule)
                .where(Schedule.user_id == user.id)
                .where(Schedule.date >= today)
                .order_by(Schedule.date)
            ).first()
            
            # Manual construction to ensure clean serialization and avoid circular dependency issues
            user_data = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "created_at": user.created_at,
                "role_system": user.role_system,
                "target_hours_per_month": user.target_hours_per_month,
            "target_shifts_per_month": user.target_shifts_per_month,
            "is_active": user.is_active,
            "job_roles": [r.id for r in user.job_roles]
            }
            
            if next_shift:
                shift_def = self.session.get(ShiftDefinition, next_shift.shift_def_id)
                role = self.session.get(JobRole, next_shift.role_id)
                
                if shift_def and role:
                   user_data["next_shift"] = NextShiftInfo(
                       date=next_shift.date,
                       start_time=shift_def.start_time.strftime("%H:%M"),
                       end_time=shift_def.end_time.strftime("%H:%M"),
                       shift_name=shift_def.name,
                       role_name=role.name
                   )
            
            result.append(user_data)
            
        return result

    def get_user_stats(self, user_id: UUID) -> dict:
        from sqlalchemy import func

        
        # 1. Total shifts completed (from Attendance)
        total_shifts = self.session.exec(
            select(func.count(Attendance.id))
            .where(Attendance.user_id == user_id)
            .where(Attendance.status == AttendanceStatus.CONFIRMED)
        ).one()
        
        # 2. Total hours (approximate from Attendance check in/out)
        # SQLModel doesn't easily support complex time diff sums in all DBs, 
        # so let's fetch and calc in python for now or use raw SQL.
        # For simplicity/safety across DBs (sqlite/postgres): fetch all confirmed.
        attendances = self.session.exec(
            select(Attendance)
            .where(Attendance.user_id == user_id)
            .where(Attendance.status == AttendanceStatus.CONFIRMED)
        ).all()
        
        total_hours = 0.0
        for att in attendances:
            start_dt = datetime.combine(att.date, att.check_in)
            end_dt = datetime.combine(att.date, att.check_out)
            if end_dt <= start_dt:
                 end_dt += timedelta(days=1)
            total_hours += (end_dt - start_dt).total_seconds() / 3600
            
        # 3. Monthly breakdown (last 6 months)
        # We can use Schedule or Attendance. "Number of shifts in previous months" usually implies completed.
        # Let's use Attendance.
        
        today = date.today()
        monthly_stats = []
        for i in range(6):
            # i=0 is current month, i=1 is previous...
            # Calculate month start/end
            month_date = today.replace(day=1) 
            # Go back i months
            # Simplified decrement
            y = month_date.year
            m = month_date.month - i
            while m <= 0:
                m += 12
                y -= 1
            
            start_of_month = date(y, m, 1)
            # End of month
            if m == 12:
                end_of_month = date(y+1, 1, 1) - timedelta(days=1)
            else:
                end_of_month = date(y, m+1, 1) - timedelta(days=1)
                
            count = self.session.exec(
                 select(func.count(Attendance.id))
                .where(Attendance.user_id == user_id)
                .where(Attendance.status == AttendanceStatus.CONFIRMED)
                .where(Attendance.date >= start_of_month)
                .where(Attendance.date <= end_of_month)
            ).one()
            
            monthly_stats.append({
                "month": start_of_month.strftime("%Y-%m"),
                "count": count
            })
            
        return {
            "total_shifts_completed": total_shifts,
            "total_hours_worked": round(total_hours, 1),
            "monthly_shifts": monthly_stats
        }

    def get_dashboard_home(self, target_date: Optional[date] = None) -> dict:
        today = target_date if target_date else date.today()
        yesterday = today - timedelta(days=1)
        
        # 1. Working today
        # Get schedules for today
        schedules = self.session.exec(
            select(Schedule)
            .where(Schedule.date == today)
            .join(User, Schedule.user_id == User.id)
            .where(User.is_active == True)
        ).all()
        
        working_today = []
        for sch in schedules:
            user = sch.user
            role = self.session.get(JobRole, sch.role_id)
            shift = self.session.get(ShiftDefinition, sch.shift_def_id)
            
            if user and role and shift:
                working_today.append({
                    "id": sch.id,
                    "date": sch.date,
                    "shift_def_id": sch.shift_def_id,
                    "user_id": sch.user_id,
                    "role_id": sch.role_id,
                    "is_published": sch.is_published,
                    "user_name": user.full_name,
                    "role_name": role.name,
                    "shift_name": shift.name,
                    "start_time": shift.start_time,
                    "end_time": shift.end_time
                })
                
        # 2. Missing confirmations from yesterday
        # Get actual PENDING records from yesterday
        pending_attendances = self.session.exec(
             select(Attendance)
             .where(Attendance.date == yesterday)
             .where(Attendance.status == AttendanceStatus.PENDING)
        ).all()
        
        missing_responses = []
        for att in pending_attendances:
             missing_responses.append({
                 "id": att.id,
                 "user_id": att.user_id,
                 "user_name": att.user.full_name if att.user else "Nieznany",
                 "date": att.date,
                 "check_in": att.check_in,
                 "check_out": att.check_out,
                 "was_scheduled": att.was_scheduled,
                 "status": att.status,
                 "created_at": att.created_at
             })
             
        # 3. Open Giveaways
        # Reuse logic from get_open_giveaways but keep it efficient if needed
        # Calling self.get_open_giveaways() might be slightly inefficient due to re-querying session, 
        # but it keeps logic DRY. For now, let's call it.
        # Alternatively, duplicate the simple select if get_open_giveaways does heavy suggestion logic.
        # get_open_giveaways does suggestions. We probably don't need suggestions on the Dashboard Home widget, just the list.
        # So let's do a lightweight fetch here.
        
        from ..models import ShiftGiveaway, GiveawayStatus
        open_giveaways_db = self.session.exec(
            select(ShiftGiveaway).where(ShiftGiveaway.status == GiveawayStatus.OPEN)
        ).all()
        
        open_giveaways = []
        for g in open_giveaways_db:
             s = g.schedule
             if not s: continue
             
             shift = self.session.get(ShiftDefinition, s.shift_def_id)
             role = self.session.get(JobRole, s.role_id)
             offerer = self.session.get(User, g.offered_by)
             
             open_giveaways.append({
                "id": g.id,
                "schedule_id": g.schedule_id,
                "offered_by": g.offered_by,
                "offered_by_name": offerer.full_name if offerer else "",
                "status": g.status.value,
                "created_at": g.created_at,
                "taken_by": g.taken_by,
                # Schedule details
                "date": s.date,
                "shift_name": shift.name if shift else None,
                "role_name": role.name if role else None,
                "start_time": shift.start_time.strftime("%H:%M") if shift else None,
                "end_time": shift.end_time.strftime("%H:%M") if shift else None,
             })

        return {
            "working_today": working_today,
            "missing_confirmations": missing_responses,
            "open_giveaways": open_giveaways
        }

    # --- Shift Giveaway ---
    def get_open_giveaways(self) -> List[dict]:
        from ..models import ShiftGiveaway, GiveawayStatus, Availability
        
        giveaways = self.session.exec(
            select(ShiftGiveaway).where(ShiftGiveaway.status == GiveawayStatus.OPEN)
        ).all()
        
        result = []
        for g in giveaways:
            schedule = g.schedule
            if not schedule:
                continue
            
            shift = self.session.get(ShiftDefinition, schedule.shift_def_id)
            role = self.session.get(JobRole, schedule.role_id)
            offerer = self.session.get(User, g.offered_by)
            
            # Build suggestions: active employees with availability for this date + same role
            eligible_users = self.session.exec(
                select(User)
                .where(User.role_system == RoleSystem.EMPLOYEE)
                .where(User.is_active == True)
                .where(User.id != g.offered_by)
            ).all()
            
            suggestions = []
            for u in eligible_users:
                # Check if user has the required role
                if schedule.role_id not in [r.id for r in u.job_roles]:
                    continue
                
                # Check availability for the date
                avail = self.session.exec(
                    select(Availability).where(
                        Availability.user_id == u.id,
                        Availability.date == schedule.date
                    )
                ).first()
                
                # Check if already scheduled on that date
                already_scheduled = self.session.exec(
                    select(Schedule).where(
                        Schedule.user_id == u.id,
                        Schedule.date == schedule.date
                    )
                ).first()
                
                avail_status = avail.status if avail else "UNKNOWN"
                if already_scheduled:
                    avail_status = "ALREADY_SCHEDULED"
                
                suggestions.append({
                    "user_id": u.id,
                    "full_name": u.full_name,
                    "availability_status": avail_status
                })
            
            # Sort: AVAILABLE first, then UNKNOWN, then ALREADY_SCHEDULED
            priority = {"AVAILABLE": 0, "PREFERRED": 1, "UNKNOWN": 2, "UNAVAILABLE": 3, "ALREADY_SCHEDULED": 4}
            suggestions.sort(key=lambda s: priority.get(s["availability_status"], 5))
            
            result.append({
                "id": g.id,
                "schedule_id": g.schedule_id,
                "offered_by": g.offered_by,
                "offered_by_name": offerer.full_name if offerer else "",
                "status": g.status.value,
                "created_at": g.created_at,
                "taken_by": g.taken_by,
                "date": schedule.date,
                "shift_name": shift.name if shift else None,
                "role_name": role.name if role else None,
                "start_time": shift.start_time.strftime("%H:%M") if shift else None,
                "end_time": shift.end_time.strftime("%H:%M") if shift else None,
                "suggestions": suggestions
            })
        
        return result

    def reassign_giveaway(self, giveaway_id: UUID, new_user_id: UUID) -> dict:
        from ..models import ShiftGiveaway, GiveawayStatus
        
        giveaway = self.session.get(ShiftGiveaway, giveaway_id)
        if not giveaway:
            raise HTTPException(status_code=404, detail="Giveaway not found")
        
        if giveaway.status != GiveawayStatus.OPEN:
            raise HTTPException(status_code=400, detail="Giveaway is not open")
        
        schedule = giveaway.schedule
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        # Reassign the schedule to the new user
        schedule.user_id = new_user_id
        giveaway.status = GiveawayStatus.TAKEN
        giveaway.taken_by = new_user_id
        
        self.session.add(schedule)
        self.session.add(giveaway)
        self.session.commit()
        
        new_user = self.session.get(User, new_user_id)
        return {
            "status": "reassigned",
            "new_user_name": new_user.full_name if new_user else ""
        }

    def get_available_employees_for_shift(self, date_in: date, shift_def_id: int) -> List[dict]:
        from ..models import Availability, Schedule, ShiftDefinition, JobRole
        from calendar import monthrange
        from datetime import datetime, timedelta
        
        # Calculate hours_this_month
        first_day = date(date_in.year, date_in.month, 1)
        last_day = date(date_in.year, date_in.month, monthrange(date_in.year, date_in.month)[1])
        
        schedules = self.session.exec(
            select(Schedule).where(
                Schedule.date >= first_day,
                Schedule.date <= last_day
            )
        ).all()
        
        all_shifts = self.session.exec(select(ShiftDefinition)).all()
        shift_map = {s.id: s for s in all_shifts}
        
        hours_by_user = {}
        for schedule in schedules:
            uid = str(schedule.user_id)
            shift = shift_map.get(schedule.shift_def_id)
            if not shift:
                continue
            
            start_dt = datetime.combine(date.today(), shift.start_time)
            end_dt = datetime.combine(date.today(), shift.end_time)
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)
            duration_hours = (end_dt - start_dt).total_seconds() / 3600
            
            hours_by_user[uid] = hours_by_user.get(uid, 0.0) + duration_hours

        # Get employees
        employees = self.session.exec(
            select(User)
            .where(User.role_system == RoleSystem.EMPLOYEE)
            .where(User.is_active == True)
        ).all()
        
        result = []
        for u in employees:
            avail = self.session.exec(
                select(Availability).where(
                    Availability.user_id == u.id,
                    Availability.date == date_in,
                    Availability.shift_def_id == shift_def_id
                )
            ).first()
            
            already_scheduled_this = self.session.exec(
                select(Schedule).where(
                    Schedule.user_id == u.id,
                    Schedule.date == date_in,
                    Schedule.shift_def_id == shift_def_id
                )
            ).first()
            
            already_scheduled_other = self.session.exec(
                select(Schedule).where(
                    Schedule.user_id == u.id,
                    Schedule.date == date_in,
                    Schedule.shift_def_id != shift_def_id
                )
            ).first()
            
            status = avail.status.value if avail else "UNKNOWN"
            if already_scheduled_this:
                status = "ALREADY_SCHEDULED_THIS"
            elif already_scheduled_other:
                status = "ALREADY_SCHEDULED_OTHER"
                
            roles_list = []
            for r in u.job_roles:
                roles_list.append({
                    "id": r.id,
                    "name": r.name,
                    "color_hex": r.color_hex
                })
                
            result.append({
                "user_id": str(u.id),
                "full_name": u.full_name,
                "availability_status": status,
                "job_roles": roles_list,
                "target_hours": u.target_hours_per_month,
                "hours_this_month": round(hours_by_user.get(str(u.id), 0.0), 1)
            })
            
        priority = {
            "PREFERRED": 0, 
            "AVAILABLE": 1, 
            "UNKNOWN": 2, 
            "UNAVAILABLE": 3, 
            "ALREADY_SCHEDULED_OTHER": 4, 
            "ALREADY_SCHEDULED_THIS": 5
        }
        result.sort(key=lambda x: priority.get(x["availability_status"], 9))
        return result

    def cancel_giveaway(self, giveaway_id: UUID):
        from ..models import ShiftGiveaway, GiveawayStatus
        
        giveaway = self.session.get(ShiftGiveaway, giveaway_id)
        if not giveaway:
            raise HTTPException(status_code=404, detail="Giveaway not found")
        
        giveaway.status = GiveawayStatus.CANCELLED
        self.session.add(giveaway)
        self.session.commit()

    def get_all_leave_requests(self, status: str = None):
        from sqlmodel import select
        from ..models import LeaveRequest, LeaveStatus, User
        
        query = select(LeaveRequest)
        if status:
            query = query.where(LeaveRequest.status == LeaveStatus(status))
        query = query.order_by(LeaveRequest.start_date.desc())
        
        requests = self.session.exec(query).all()
        result = []
        for r in requests:
            user = self.session.get(User, r.user_id)
            result.append({"req": r, "user": user})
        return result

    def process_leave_request(self, request_id: UUID, approved: bool, manager_id: UUID, background_tasks=None):
        from sqlmodel import select
        from ..models import LeaveRequest, LeaveStatus, Availability, AvailabilityStatus, ShiftDefinition
        from datetime import datetime, timedelta
        
        req = self.session.get(LeaveRequest, request_id)
        if not req:
            raise HTTPException(status_code=404, detail="Leave request not found")
            
        if req.status != LeaveStatus.PENDING:
            raise HTTPException(status_code=400, detail="Only PENDING requests can be processed")
            
        req.status = LeaveStatus.APPROVED if approved else LeaveStatus.REJECTED
        req.reviewed_by = manager_id
        req.reviewed_at = datetime.utcnow()
        self.session.add(req)
        
        if approved:
            # Auto-Set Availability on Approval
            shifts = self.session.exec(select(ShiftDefinition)).all()
            
            curr_date = req.start_date
            while curr_date <= req.end_date:
                for shift in shifts:
                    avail = self.session.exec(
                        select(Availability).where(
                            Availability.user_id == req.user_id,
                            Availability.date == curr_date,
                            Availability.shift_def_id == shift.id
                        )
                    ).first()
                    
                    if avail:
                        avail.status = AvailabilityStatus.UNAVAILABLE
                        self.session.add(avail)
                    else:
                        new_avail = Availability(
                            user_id=req.user_id,
                            date=curr_date,
                            shift_def_id=shift.id,
                            status=AvailabilityStatus.UNAVAILABLE
                        )
                        self.session.add(new_avail)
                curr_date += timedelta(days=1)
                
        # Notify the employee
        from ..models import Notification
        status_text = "zaakceptowany" if approved else "odrzucony"
        title = "Wniosek urlopowy rozpatrzony"
        body = f"Twój wniosek urlopowy od {req.start_date} do {req.end_date} został {status_text}."
        
        notif = Notification(
            user_id=req.user_id,
            title=title,
            body=body,
        )
        self.session.add(notif)
        
        if background_tasks:
            from .push_service import PushService, send_push_to_tokens
            push_svc = PushService(self.session)
            tokens = push_svc._get_user_tokens(req.user_id)
            if tokens:
                background_tasks.add_task(send_push_to_tokens, tokens, title, body)
                
                
        self.session.commit()
        return req

    def get_leave_calendar(self, year: int, month: int):
        from sqlmodel import select
        from ..models import LeaveRequest, LeaveStatus, User
        import calendar
        from datetime import date
        
        last_day = calendar.monthrange(year, month)[1]
        start_date = date(year, month, 1)
        end_date = date(year, month, last_day)
        
        requests = self.session.exec(
            select(LeaveRequest).where(
                LeaveRequest.start_date <= end_date,
                LeaveRequest.end_date >= start_date,
                LeaveRequest.status == LeaveStatus.APPROVED
            )
        ).all()
        
        entries = []
        for req in requests:
            user = self.session.get(User, req.user_id)
            entries.append({
                "user_id": str(req.user_id),
                "user_name": user.full_name,
                "start_date": req.start_date.isoformat(),
                "end_date": req.end_date.isoformat(),
                "status": str(req.status.value)
            })
            
        return {"entries": entries}

