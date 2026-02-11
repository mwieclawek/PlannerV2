from typing import List, Optional
from uuid import UUID
from datetime import datetime, date
from sqlmodel import Session, select
from fastapi import HTTPException
from ..models import JobRole, ShiftDefinition, StaffingRequirement, RestaurantConfig, User, UserJobRoleLink
from ..schemas import JobRoleCreate, ShiftDefCreate, RequirementCreate, ConfigUpdate, UserUpdate

class ManagerService:
    def __init__(self, session: Session):
        self.session = session

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
