from pydantic import BaseModel, field_validator, ValidationInfo
from datetime import datetime, date, time
from typing import List, Optional
from uuid import UUID
from backend.app.models import RoleSystem, AvailabilityStatus

# ... (Previous imports remain, but need field_validator, ValidationInfo)

# --- Auth ---
class Token(BaseModel):
    access_token: str
    token_type: str

class UserBase(BaseModel):
    email: str
    full_name: str
    role_system: RoleSystem

class UserCreate(UserBase):
    password: str
    manager_pin: Optional[str] = None

class UserResponse(UserBase):
    id: UUID
    job_roles: List[int]

    class Config:
        from_attributes = True

# --- Roles ---
class JobRoleBase(BaseModel):
    name: str
    color_hex: str

class JobRoleCreate(JobRoleBase):
    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        return v

class JobRoleResponse(JobRoleBase):
    id: int

    class Config:
        from_attributes = True

# --- Shifts ---
class ShiftDefBase(BaseModel):
    name: str
    start_time: str # HH:MM - handled as string in input
    end_time: str   # HH:MM

class ShiftDefCreate(ShiftDefBase):
    @field_validator('start_time', 'end_time')
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError("Time must be in HH:MM format")
        return v

class ShiftDefResponse(BaseModel):
    id: int
    name: str
    start_time: time
    end_time: time

    class Config:
        from_attributes = True

# --- Availability ---
class AvailabilityBase(BaseModel):
    date: date
    shift_def_id: int
    status: AvailabilityStatus

class AvailabilityUpdate(AvailabilityBase):
    pass

class AvailabilityResponse(AvailabilityBase):
    user_id: UUID

    class Config:
        from_attributes = True

# --- Requirements ---
class RequirementBase(BaseModel):
    date: date
    shift_def_id: int
    role_id: int
    min_count: int

class RequirementCreate(RequirementBase):
    @field_validator('min_count')
    @classmethod
    def min_count_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError('min_count must be non-negative')
        return v

class RequirementResponse(RequirementBase):
    id: UUID

    class Config:
        from_attributes = True

# --- Scheduler ---
class GenerateRequest(BaseModel):
    start_date: date
    end_date: date

class ScheduleBatchItem(BaseModel):
    date: date
    shift_def_id: int
    user_id: UUID
    role_id: int

class BatchSaveRequest(BaseModel):
    start_date: date
    end_date: date
    items: List[ScheduleBatchItem]

class ScheduleResponse(BaseModel):
    id: UUID
    date: date
    shift_def_id: int
    user_id: UUID
    role_id: int
    is_published: bool
    user_name: str
    role_name: str
    shift_name: str

class EmployeeScheduleResponse(BaseModel):
    id: UUID
    date: date
    shift_name: str
    role_name: str
    start_time: str
    end_time: str

# --- Restaurant Config ---
class ConfigBase(BaseModel):
    name: str
    opening_hours: str
    address: Optional[str] = None

class ConfigUpdate(ConfigBase):
    pass

class ConfigResponse(ConfigBase):
    id: int

    class Config:
        from_attributes = True

# --- User Management ---
class UserRolesUpdate(BaseModel):
    role_ids: List[int]

class PasswordReset(BaseModel):
    new_password: str

class ManualAssignment(BaseModel):
    date: date
    shift_def_id: int
    user_id: UUID
    role_id: int
