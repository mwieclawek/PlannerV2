from datetime import datetime, date as date_type, time
from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from ..models import AvailabilityStatus, GiveawayStatus
from ..services.solver import (
    SolverAvailabilityItem,
    SolverEmployeeItem,
    SolverJobPayload,
    SolverLeaveDayItem,
    SolverRequirementItem,
    SolverRoleItem,
    SolverShiftItem,
)


# --- Shifts ---
class ShiftDefBase(BaseModel):
    name: str
    start_time: str  # HH:MM - handled as string in input
    end_time: str    # HH:MM
    applicable_days: List[int] = [0, 1, 2, 3, 4, 5, 6]  # 0=Mon, 6=Sun, default all days
    allowed_role_ids: List[int] = []


class ShiftDefCreate(ShiftDefBase):
    @field_validator('start_time', 'end_time')
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        # Try HH:MM first
        try:
            datetime.strptime(v, "%H:%M")
            return v
        except ValueError:
            pass

        # Try HH:MM:SS
        try:
            val = datetime.strptime(v, "%H:%M:%S")
            return val.strftime("%H:%M")  # standardized to HH:MM
        except ValueError:
            raise ValueError("Time must be in HH:MM or HH:MM:SS format")


class ShiftDefResponse(BaseModel):
    id: int
    name: str
    start_time: time
    end_time: time
    applicable_days: List[int] = [0, 1, 2, 3, 4, 5, 6]
    allowed_role_ids: List[int] = []

    @model_validator(mode='before')
    @classmethod
    def extract_custom_fields(cls, data):
        if hasattr(data, 'days'):
            days = [d.day_of_week for d in getattr(data, 'days', [])]
            roles = [r.id for r in getattr(data, 'allowed_roles', [])]
            if not days:  # default if no specific days are set
                days = [0, 1, 2, 3, 4, 5, 6]
            if not isinstance(data, dict):
                data.__dict__['applicable_days'] = days
                data.__dict__['allowed_role_ids'] = roles
        elif isinstance(data, dict):
            if 'days' in data:
                days = [d.day_of_week if hasattr(d, 'day_of_week') else d.get('day_of_week') for d in data.get('days', [])]
                if not days:
                    days = [0, 1, 2, 3, 4, 5, 6]
                data['applicable_days'] = days
            if 'allowed_roles' in data:
                data['allowed_role_ids'] = [r.id if hasattr(r, 'id') else r.get('id') for r in data.get('allowed_roles', [])]
        return data

    @field_validator('applicable_days', mode='before')
    @classmethod
    def parse_applicable_days(cls, v):
        if isinstance(v, str):
            return [int(x) for x in v.split(',') if x.strip()]
        return v

    model_config = ConfigDict(from_attributes=True)


# --- Availability ---
class AvailabilityBase(BaseModel):
    date: date_type
    shift_def_id: int
    status: AvailabilityStatus


class AvailabilityUpdate(AvailabilityBase):
    pass


class AvailabilityResponse(AvailabilityBase):
    user_id: UUID

    model_config = ConfigDict(from_attributes=True)


# --- Requirements ---
class RequirementBase(BaseModel):
    date: Optional[date_type] = None
    day_of_week: Optional[int] = None
    shift_def_id: int
    role_id: int
    min_count: int

    @model_validator(mode='after')
    def check_date_or_day(self) -> 'RequirementBase':
        if self.date is None and self.day_of_week is None:
            raise ValueError('Either date or day_of_week must be provided')
        if self.date is not None and self.day_of_week is not None:
            raise ValueError('Cannot provide both date and day_of_week')
        return self

    @field_validator('day_of_week')
    @classmethod
    def validate_day(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 0 or v > 6):
            raise ValueError('day_of_week must be between 0 and 6')
        return v


class RequirementCreate(RequirementBase):
    @field_validator('min_count')
    @classmethod
    def min_count_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError('min_count must be non-negative')
        return v


class RequirementResponse(RequirementBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


# --- Scheduler ---
class GenerateRequest(BaseModel):
    start_date: date_type
    end_date: date_type


class ScheduleBatchItem(BaseModel):
    date: date_type
    shift_def_id: int
    user_id: UUID
    role_id: int


class BatchSaveRequest(BaseModel):
    start_date: date_type
    end_date: date_type
    items: List[ScheduleBatchItem]
    is_published: bool = False


class LaborCostSimulationRequest(BaseModel):
    start_date: date_type
    end_date: date_type
    items: Optional[List[ScheduleBatchItem]] = None


class PublishScheduleRequest(BaseModel):
    start_date: Optional[date_type] = None
    end_date: Optional[date_type] = None


class ScheduleResponse(BaseModel):
    id: UUID
    date: date_type
    shift_def_id: int
    user_id: UUID
    role_id: int
    is_published: bool
    user_name: str
    role_name: str
    shift_name: str
    start_time: time
    end_time: time
    is_on_giveaway: bool = False


class CoworkerEntry(BaseModel):
    name: str
    role_name: str


class EmployeeScheduleResponse(BaseModel):
    id: UUID
    date: date_type
    shift_name: str
    role_name: str
    start_time: str
    end_time: str
    is_on_giveaway: bool = False
    coworkers: List[CoworkerEntry] = []
    role_id: Optional[int] = None
    shift_def_id: Optional[int] = None


class ManualAssignment(BaseModel):
    date: date_type
    shift_def_id: int
    user_id: UUID
    role_id: int


# --- Shift Giveaway ---
class OfferGiveawayRequest(BaseModel):
    target_shift_id: Optional[Union[UUID, str]] = None


class ShiftGiveawayResponse(BaseModel):
    id: UUID
    schedule_id: UUID
    offered_by: UUID
    offered_by_name: str = ""
    status: GiveawayStatus
    created_at: datetime
    taken_by: Optional[UUID] = None
    taken_by_name: Optional[str] = None
    target_shift_id: Optional[Union[UUID, str]] = None
    # Schedule details
    date: Optional[date_type] = None
    shift_name: Optional[str] = None
    role_name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class GiveawaySuggestion(BaseModel):
    user_id: UUID
    full_name: str
    availability_status: Optional[str] = None


class ShiftGiveawayWithSuggestions(ShiftGiveawayResponse):
    suggestions: List[GiveawaySuggestion] = []


class GiveawayReassignRequest(BaseModel):
    new_user_id: Optional[UUID] = None
    target_shift_id: Optional[Union[UUID, str]] = None


# --- Shift Audit Log ---
class ShiftAuditLogResponse(BaseModel):
    id: int
    restaurant_id: int
    shift_id: str
    schedule_id: Optional[UUID] = None
    shift_def_id: Optional[int] = None
    date: Optional[date_type] = None
    changed_by_user_id: Optional[UUID] = None
    changed_by_user_name: Optional[str] = None
    action: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    created_at: datetime
    shift_name_snapshot: Optional[str] = None
    role_name_snapshot: Optional[str] = None
    target_user_name: Optional[str] = None
    actor_name: Optional[str] = None
    summary: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --- Leave Requests ---
class LeaveRequestCreate(BaseModel):
    start_date: date_type
    end_date: date_type
    reason: Optional[str] = None

    @model_validator(mode='after')
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date")
        return self


class LeaveRequestResponse(BaseModel):
    id: UUID
    user_id: UUID
    user_name: str
    start_date: date_type
    end_date: date_type
    reason: Optional[str]
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime]
