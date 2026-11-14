from datetime import datetime, date as date_type, time
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from ..models import AttendanceStatus, ShiftPeriodType, HaccpLogType
from .scheduling import ScheduleResponse, ShiftGiveawayResponse, LeaveRequestResponse


# --- Attendance ---
class AttendanceBase(BaseModel):
    user_id: UUID
    date: date_type
    check_in: time
    check_out: time
    was_scheduled: bool = True
    status: AttendanceStatus = AttendanceStatus.CONFIRMED
    schedule_id: Optional[UUID] = None
    checklist_skip_reason: Optional[str] = None
    is_absent: bool = False
    absence_reason: Optional[str] = None


class AttendanceCreate(AttendanceBase):
    pass


class AttendanceResponse(AttendanceBase):
    id: UUID
    created_at: datetime
    user_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  Module A: Payroll, Settlements & Labor Cost Lite
# ═══════════════════════════════════════════════════════════════════════════════

class DailyCloseoutCreate(BaseModel):
    date: date_type
    daily_revenue: float
    tip_pool: float = 0.0
    notes: Optional[str] = None

    @field_validator('daily_revenue', 'tip_pool')
    @classmethod
    def non_negative_values(cls, v: float) -> float:
        if v < 0:
            raise ValueError('Value must be non-negative')
        return round(v, 2)


class EmployeeTipAllocation(BaseModel):
    user_id: UUID
    user_name: str
    confirmed_hours: float
    allocated_tip: float


class DailyCloseoutSummaryResponse(BaseModel):
    id: Optional[UUID] = None
    date: date_type
    daily_revenue: float = 0.0
    tip_pool: float = 0.0
    notes: Optional[str] = None
    confirmed_hours: float = 0.0
    scheduled_hours: float = 0.0
    labor_cost: float = 0.0
    labor_cost_pct: float = 0.0
    is_closed_out: bool = False
    tip_allocations: List[EmployeeTipAllocation] = []


class DashboardHomeResponse(BaseModel):
    working_today: List[ScheduleResponse]
    missing_confirmations: List[AttendanceResponse]
    open_giveaways: List[ShiftGiveawayResponse]
    pending_leave_requests: List[LeaveRequestResponse] = []
    daily_closeout: Optional[DailyCloseoutSummaryResponse] = None


class PayrollEmployeeItem(BaseModel):
    user_id: UUID
    user_name: str
    hourly_rate: float
    confirmed_hours: float
    pending_hours: float
    shifts_count: int
    base_pay: float
    allocated_tips: float
    total_pay: float


class MonthlyPayrollResponse(BaseModel):
    year: int
    month: int
    items: List[PayrollEmployeeItem]
    total_confirmed_hours: float
    total_pending_hours: float
    total_base_pay: float
    total_tips: float
    total_payroll: float
    total_monthly_revenue: float = 0.0
    monthly_labor_cost_pct: float = 0.0


class EmployeeDailyEarningItem(BaseModel):
    date: date_type
    status: str
    hours: float
    hourly_rate: float
    base_pay: float
    allocated_tip: float
    total_pay: float


class EmployeeMonthlyEarningsResponse(BaseModel):
    year: int
    month: int
    user_id: UUID
    user_name: str
    hourly_rate: float
    confirmed_hours: float
    pending_hours: float
    base_pay: float
    allocated_tips: float
    total_pay: float
    daily_breakdown: List[EmployeeDailyEarningItem] = []


# ═══════════════════════════════════════════════════════════════════════════════
#  Module B: Operational Checklists & Digital HACCP Registry
# ═══════════════════════════════════════════════════════════════════════════════

class ChecklistItemCreate(BaseModel):
    title: str
    is_mandatory: bool = True
    sort_order: int = 0

    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Checklist item title cannot be empty')
        return v


class ChecklistItemResponse(BaseModel):
    id: UUID
    template_id: UUID
    title: str
    is_mandatory: bool
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class ChecklistTemplateCreate(BaseModel):
    title: str
    description: Optional[str] = None
    role_id: Optional[int] = None
    shift_period: ShiftPeriodType = ShiftPeriodType.OPENING
    is_mandatory: bool = True
    is_active: bool = True
    items: List[ChecklistItemCreate] = []

    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Checklist template title cannot be empty')
        return v


class ChecklistTemplateResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    shift_period: ShiftPeriodType
    is_mandatory: bool
    is_active: bool
    created_at: datetime
    items: List[ChecklistItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class EmployeeChecklistItemView(BaseModel):
    id: UUID
    template_id: UUID
    title: str
    is_mandatory: bool
    sort_order: int
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    completed_by_user_id: Optional[UUID] = None
    completed_by_user_name: Optional[str] = None


class EmployeeChecklistView(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    shift_period: ShiftPeriodType
    is_mandatory: bool
    date: date_type
    items: List[EmployeeChecklistItemView] = []
    completed_count: int = 0
    total_count: int = 0


class ChecklistToggleRequest(BaseModel):
    date: Optional[date_type] = None
    is_completed: Optional[bool] = None


class MissingChecklistItemInfo(BaseModel):
    template_id: UUID
    template_title: str
    item_id: UUID
    item_title: str
    shift_period: ShiftPeriodType


class ClockoutValidationResponse(BaseModel):
    date: date_type
    all_mandatory_completed: bool
    missing_mandatory_count: int
    missing_items: List[MissingChecklistItemInfo] = []


class HaccpDeviceCreate(BaseModel):
    name: str
    min_temp: float = 0.0
    max_temp: float = 4.0
    is_active: bool = True

    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Device name cannot be empty')
        return v

    @model_validator(mode='after')
    def check_temp_range(self):
        if self.max_temp < self.min_temp:
            raise ValueError('max_temp must be >= min_temp')
        return self


class HaccpDeviceResponse(BaseModel):
    id: UUID
    name: str
    min_temp: float
    max_temp: float
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HaccpLogCreate(BaseModel):
    log_type: HaccpLogType = HaccpLogType.TEMPERATURE
    device_id: Optional[UUID] = None
    device_name: Optional[str] = None
    min_temp: Optional[float] = None
    max_temp: Optional[float] = None
    measured_temp: Optional[float] = None
    corrective_action: Optional[str] = None
    notes: Optional[str] = None


class HaccpLogResponse(BaseModel):
    id: UUID
    log_type: HaccpLogType
    device_id: Optional[UUID] = None
    device_name: str
    min_temp: Optional[float] = None
    max_temp: Optional[float] = None
    measured_temp: Optional[float] = None
    is_within_norm: bool
    corrective_action: Optional[str] = None
    user_id: UUID
    user_name: str = ""
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  Module C: Announcement Board with Read Receipts
# ═══════════════════════════════════════════════════════════════════════════════

class AnnouncementCreate(BaseModel):
    title: str
    content: str
    is_pinned: bool = False

    @field_validator('title', 'content')
    @classmethod
    def not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Field cannot be empty')
        return v


class AnnouncementReaderInfo(BaseModel):
    user_id: UUID
    user_name: str
    read_at: Optional[datetime] = None


class AnnouncementManagerResponse(BaseModel):
    id: UUID
    title: str
    content: str
    is_pinned: bool
    author_id: UUID
    author_name: str
    created_at: datetime
    read_count: int
    total_target_count: int
    read_by: List[AnnouncementReaderInfo] = []
    unread_by: List[AnnouncementReaderInfo] = []


class AnnouncementEmployeeResponse(BaseModel):
    id: UUID
    title: str
    content: str
    is_pinned: bool
    author_id: UUID
    author_name: str
    created_at: datetime
    is_read: bool
    read_at: Optional[datetime] = None
