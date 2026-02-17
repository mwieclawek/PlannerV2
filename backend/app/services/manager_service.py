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
        
        user = User(
            username=user_in.username,
            email=user_in.email,
            password_hash=hashed_password,
            full_name=user_in.full_name,
            role_system=user_in.role_system,
            target_hours_per_month=user_in.target_hours_per_month,
            target_shifts_per_month=user_in.target_shifts_per_month
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

        # Convert List[int] to comma-separated string
        applicable_days_str = ",".join(str(d) for d in shift_in.applicable_days)
        
        shift = ShiftDefinition(
            name=shift_in.name, 
            start_time=s_time, 
            end_time=e_time,
            applicable_days=applicable_days_str
        )
        self.session.add(shift)
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

        # Convert List[int] to comma-separated string
        applicable_days_str = ",".join(str(d) for d in shift_in.applicable_days)

        shift.name = shift_in.name
        shift.start_time = s_time
        shift.end_time = e_time
        shift.applicable_days = applicable_days_str
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
        for r in reqs:
            query = select(StaffingRequirement).where(
                StaffingRequirement.shift_def_id == r.shift_def_id,
                StaffingRequirement.role_id == r.role_id
            )
            
            if r.date:
                query = query.where(StaffingRequirement.date == r.date)
            elif r.day_of_week is not None:
                query = query.where(StaffingRequirement.day_of_week == r.day_of_week)
            else:
                 # Should be caught by schema validation, but safe fallback or error
                 continue

            existing = self.session.exec(query).first()
            
            if existing:
                existing.min_count = r.min_count
                self.session.add(existing)
                results.append(existing)
            else:
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
        if not config:
            data = update.dict(exclude_unset=True)
            if "name" not in data:
                 data["name"] = "My Restaurant"
            config = RestaurantConfig(id=1, **data)
            self.session.add(config)
        else:
            data = update.dict(exclude_unset=True)
            for key, value in data.items():
                setattr(config, key, value)
            self.session.add(config)
        self.session.commit()
        self.session.refresh(config)
        return config

    # --- User Role Management ---
    def update_user(self, user_id: UUID, update: UserUpdate) -> User:
        user = self.session.get(User, user_id)
        if not user:
             raise HTTPException(status_code=404, detail="User not found")
        data = update.dict(exclude_unset=True)
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

    def get_users_with_shifts(self) -> List[dict]:
        """Get all users with their next upcoming shift"""
        from ..models import Schedule
        from ..schemas import NextShiftInfo
        
        users = self.session.exec(select(User).where(User.role_system == RoleSystem.EMPLOYEE)).all()
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
            select(Schedule).where(Schedule.date == today)
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
             
        return {
            "working_today": working_today,
            "missing_confirmations": missing_responses
        }

