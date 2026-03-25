from pydantic import BaseModel, field_validator, model_validator, ValidationInfo
from datetime import datetime, date as date_type, time
from typing import List, Optional
from uuid import UUID
from .models import (
    RoleSystem, AvailabilityStatus, AttendanceStatus, GiveawayStatus, LeaveStatus,
    # POS v2
    TableStatus, OrderStatus, OrderItemKDSStatus, PaymentMethod,
    # Legacy (deprecated)
    KitchenOrderStatus, MenuCategory,
)

# ... (Previous imports remain, but need field_validator, ValidationInfo)

# --- Auth ---
class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class UserBase(BaseModel):
    username: str
    full_name: str
    role_system: RoleSystem
    email: Optional[str] = None  # Optional for contact
    target_hours_per_month: Optional[int] = None
    target_shifts_per_month: Optional[int] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str
    manager_pin: Optional[str] = None

    @field_validator('username')
    @classmethod
    def username_must_be_valid(cls, v: str) -> str:
        if not v or len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if ' ' in v:
            raise ValueError('Username cannot contain spaces')
        return v.lower()  # Normalize to lowercase

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class GoogleAuthRequest(BaseModel):
    auth_code: str

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    role_system: Optional[RoleSystem] = None
    target_hours_per_month: Optional[int] = None
    target_shifts_per_month: Optional[int] = None
    is_active: Optional[bool] = None

    class Config:
        from_attributes = True

# --- New Features Schemas ---

class NextShiftInfo(BaseModel):
    date: date_type
    start_time: str # HH:MM
    end_time: str   # HH:MM
    shift_name: str
    role_name: str

class UserStats(BaseModel):
    total_shifts_completed: int
    total_hours_worked: float
    # Monthly breakdown for the last 6 months
    monthly_shifts: List[dict] # [{"month": "2023-01", "count": 10}, ...]

class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    job_roles: List[int] = []
    next_shift: Optional[NextShiftInfo] = None

    @model_validator(mode='before')
    @classmethod
    def extract_role_ids(cls, data):
        """Convert JobRole ORM objects to plain int IDs."""
        if hasattr(data, 'job_roles'):
            roles = data.job_roles
            if roles and hasattr(roles[0], 'id'):
                data.__dict__['job_roles'] = [r.id for r in roles]
        elif isinstance(data, dict) and 'job_roles' in data:
            roles = data['job_roles']
            if roles and hasattr(roles[0], 'id'):
                data['job_roles'] = [r.id for r in roles]
        return data

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
    applicable_days: List[int] = [0, 1, 2, 3, 4, 5, 6]  # 0=Mon, 6=Sun, default all days

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
            return val.strftime("%H:%M") # standardized to HH:MM
        except ValueError:
            raise ValueError("Time must be in HH:MM or HH:MM:SS format")

class ShiftDefResponse(BaseModel):
    id: int
    name: str
    start_time: time
    end_time: time
    applicable_days: List[int] = [0, 1, 2, 3, 4, 5, 6]

    @model_validator(mode='before')
    @classmethod
    def extract_applicable_days(cls, data):
        if hasattr(data, 'days'):
            days = [d.day_of_week for d in getattr(data, 'days', [])]
            if not days:  # default if no specific days are set
                days = [0, 1, 2, 3, 4, 5, 6]
            if not isinstance(data, dict):
                data.__dict__['applicable_days'] = days
        elif isinstance(data, dict) and 'days' in data:
            days = [d.day_of_week if hasattr(d, 'day_of_week') else d.get('day_of_week') for d in data.get('days', [])]
            if not days:
                days = [0, 1, 2, 3, 4, 5, 6]
            data['applicable_days'] = days
        return data

    @field_validator('applicable_days', mode='before')
    @classmethod
    def parse_applicable_days(cls, v):
        if isinstance(v, str):
            return [int(x) for x in v.split(',') if x.strip()]
        return v

    class Config:
        from_attributes = True

# --- Availability ---
class AvailabilityBase(BaseModel):
    date: date_type
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

    class Config:
        from_attributes = True

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

# --- Restaurant Config ---
class ConfigBase(BaseModel):
    name: str
    opening_hours: str
    address: Optional[str] = None

class ConfigUpdate(BaseModel):
    name: Optional[str] = None
    opening_hours: Optional[str] = None
    address: Optional[str] = None
    pos_enabled: Optional[bool] = None

class ConfigResponse(ConfigBase):
    id: int
    pos_enabled: bool = False

    @model_validator(mode='before')
    @classmethod
    def extract_opening_hours(cls, data):
        if hasattr(data, 'opening_hours') and not isinstance(data.opening_hours, str):
            import json
            hours_dict = {}
            for h in data.opening_hours:
                hours_dict[str(h.day_of_week)] = {
                    "open": h.open_time.strftime("%H:%M"),
                    "close": h.close_time.strftime("%H:%M")
                }
            if not isinstance(data, dict):
                data.__dict__['opening_hours'] = json.dumps(hours_dict)
        return data

    class Config:
        from_attributes = True

# --- User Management ---
class UserRolesUpdate(BaseModel):
    role_ids: List[int]

class PasswordReset(BaseModel):
    new_password: str

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserPasswordChange(BaseModel):
    old_password: str
    new_password: str

class ManualAssignment(BaseModel):
    date: date_type
    shift_def_id: int
    user_id: UUID
    role_id: int

# --- Attendance ---
class AttendanceBase(BaseModel):
    user_id: UUID
    date: date_type
    check_in: time
    check_out: time
    was_scheduled: bool = True
    status: AttendanceStatus = AttendanceStatus.CONFIRMED
    schedule_id: Optional[UUID] = None

class AttendanceCreate(AttendanceBase):
    pass

class AttendanceResponse(AttendanceBase):
    id: UUID
    created_at: datetime
    user_name: Optional[str] = None

    class Config:
        from_attributes = True

# --- Shift Giveaway ---
class ShiftGiveawayResponse(BaseModel):
    id: UUID
    schedule_id: UUID
    offered_by: UUID
    offered_by_name: str = ""
    status: GiveawayStatus
    created_at: datetime
    taken_by: Optional[UUID] = None
    taken_by_name: Optional[str] = None
    # Schedule details
    date: Optional[date_type] = None
    shift_name: Optional[str] = None
    role_name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None

    class Config:
        from_attributes = True

class GiveawaySuggestion(BaseModel):
    user_id: UUID
    full_name: str
    availability_status: Optional[str] = None

class ShiftGiveawayWithSuggestions(ShiftGiveawayResponse):
    suggestions: List[GiveawaySuggestion] = []

class GiveawayReassignRequest(BaseModel):
    new_user_id: UUID

class DashboardHomeResponse(BaseModel):
    working_today: List[ScheduleResponse]
    missing_confirmations: List[AttendanceResponse]
    open_giveaways: List["ShiftGiveawayResponse"]
    pending_leave_requests: List["LeaveRequestResponse"] = []

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


# ── POS v2 Schemas ──────────────────────────────────────────────────────────────

# --- Table Zones ---

class TableZoneCreate(BaseModel):
    name: str
    sort_order: int = 0

class TableZoneResponse(BaseModel):
    id: UUID
    name: str
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True

# --- POS Tables ---

class PosTableCreate(BaseModel):
    name: str
    zone_id: Optional[UUID] = None
    seats: int = 4
    sort_order: int = 0

class PosTableUpdate(BaseModel):
    name: Optional[str] = None
    zone_id: Optional[UUID] = None
    seats: Optional[int] = None
    status: Optional[TableStatus] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

class PosTableResponse(BaseModel):
    id: UUID
    name: str
    zone_id: Optional[UUID] = None
    seats: int
    status: TableStatus
    sort_order: int
    is_active: bool
    zone_name: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def extract_zone_name(cls, data):
        if hasattr(data, 'zone') and data.zone:
            if not isinstance(data, dict):
                data.__dict__['zone_name'] = data.zone.name
        return data

    class Config:
        from_attributes = True

# --- Categories ---

class CategoryCreate(BaseModel):
    name: str
    color_hex: str = "#607D8B"
    icon_name: Optional[str] = None
    sort_order: int = 0

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    color_hex: Optional[str] = None
    icon_name: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

class CategoryResponse(BaseModel):
    id: int
    name: str
    color_hex: str
    icon_name: Optional[str] = None
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True

# --- Menu Items (v2) ---

class MenuItemCreateV2(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    category_id: int
    tax_rate: float = 0.23
    kitchen_print: bool = True
    bar_print: bool = False
    sort_order: int = 0
    is_active: bool = True

class MenuItemUpdateV2(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category_id: Optional[int] = None
    tax_rate: Optional[float] = None
    kitchen_print: Optional[bool] = None
    bar_print: Optional[bool] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

class MenuItemResponseV2(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    price: float
    category_id: int
    category_name: Optional[str] = None
    tax_rate: float
    kitchen_print: bool
    bar_print: bool
    sort_order: int
    is_active: bool

    @model_validator(mode='before')
    @classmethod
    def extract_category_name(cls, data):
        if hasattr(data, 'category_rel') and data.category_rel:
            if not isinstance(data, dict):
                data.__dict__['category_name'] = data.category_rel.name
        return data

    class Config:
        from_attributes = True

# --- Modifier Groups & Modifiers ---

class ModifierCreate(BaseModel):
    name: str
    price_override: float = 0.0
    sort_order: int = 0

class ModifierResponse(BaseModel):
    id: int
    group_id: int
    name: str
    price_override: float
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True

class ModifierGroupCreate(BaseModel):
    name: str
    min_select: int = 0
    max_select: int = 1
    modifiers: List[ModifierCreate] = []

class ModifierGroupResponse(BaseModel):
    id: int
    name: str
    min_select: int
    max_select: int
    is_active: bool
    modifiers: List[ModifierResponse] = []

    class Config:
        from_attributes = True

# --- Orders (v2) ---

class OrderItemModifierCreate(BaseModel):
    modifier_id: int

class OrderItemModifierResponse(BaseModel):
    id: UUID
    modifier_id: int
    modifier_name_snapshot: str
    price_snapshot: float

    class Config:
        from_attributes = True

class OrderItemCreate(BaseModel):
    menu_item_id: UUID
    quantity: int = 1
    course: int = 1
    notes: Optional[str] = None
    modifier_ids: List[int] = []

class OrderItemResponse(BaseModel):
    id: UUID
    order_id: UUID
    menu_item_id: UUID
    quantity: int
    unit_price_snapshot: float
    item_name_snapshot: str
    course: int
    notes: Optional[str] = None
    kds_status: OrderItemKDSStatus
    sent_to_kitchen_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    split_tag: Optional[str] = None
    modifiers: List[OrderItemModifierResponse] = []

    class Config:
        from_attributes = True

class OrderItemKDSStatusUpdate(BaseModel):
    kds_status: OrderItemKDSStatus

class OrderCreate(BaseModel):
    table_id: UUID
    guest_count: int = 1
    notes: Optional[str] = None
    items: List[OrderItemCreate] = []

class OrderResponse(BaseModel):
    id: UUID
    table_id: UUID
    waiter_id: UUID
    status: OrderStatus
    guest_count: int
    notes: Optional[str] = None
    discount_pct: float
    created_at: datetime
    closed_at: Optional[datetime] = None
    items: List[OrderItemResponse] = []
    table_name: Optional[str] = None
    waiter_name: Optional[str] = None
    total_amount: float = 0.0
    amount_paid: float = 0.0
    amount_due: float = 0.0

    class Config:
        from_attributes = True

class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class OrderDiscountUpdate(BaseModel):
    discount_pct: float
    manager_pin: str   # manager PIN for authorization

# --- Payments ---

class PaymentCreate(BaseModel):
    order_id: UUID
    method: PaymentMethod
    amount: float
    tip_amount: float = 0.0

class PaymentResponse(BaseModel):
    id: UUID
    order_id: UUID
    method: PaymentMethod
    amount: float
    tip_amount: float
    received_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class TipSummaryResponse(BaseModel):
    """Per-waiter tip summary for Smart Tips Tracker."""
    total_tips: float
    tip_count: int
    tips_by_method: dict = {}  # {"CASH": 5.0, "CARD": 12.0}


# ── DEPRECATED Legacy Schemas (kept for backward compat) ───────────────────────

class RestaurantTableCreate(BaseModel):
    name: str
    is_active: bool = True

class RestaurantTableResponse(BaseModel):
    id: UUID
    name: str
    is_active: bool

    class Config:
        from_attributes = True

class MenuItemCreate(BaseModel):
    name: str
    price: float
    category: MenuCategory
    is_active: bool = True

class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    category: Optional[MenuCategory] = None
    is_active: Optional[bool] = None

class MenuItemResponse(BaseModel):
    id: UUID
    name: str
    price: float
    category: Optional[MenuCategory] = None
    is_active: bool

    @model_validator(mode='before')
    @classmethod
    def derive_category_enum(cls, data):
        """Map new category_id back to legacy MenuCategory enum for compat."""
        _REVERSE_MAP = {1: "SOUPS", 2: "MAINS", 3: "DESSERTS", 4: "DRINKS"}
        try:
            cat_id = data.category_id if not isinstance(data, dict) else data.get('category_id')
        except (AttributeError, KeyError):
            cat_id = None
        if cat_id:
            val = _REVERSE_MAP.get(cat_id, "MAINS")
            if not isinstance(data, dict):
                data.__dict__['category'] = val
            else:
                data['category'] = val
        return data

    class Config:
        from_attributes = True

class KitchenOrderItemCreate(BaseModel):
    menu_item_id: UUID
    quantity: int = 1
    notes: Optional[str] = None

class KitchenOrderItemResponse(BaseModel):
    id: UUID
    order_id: UUID
    menu_item_id: UUID
    quantity: int
    notes: Optional[str] = None
    unit_price: float
    menu_item_name: Optional[str] = None

    class Config:
        from_attributes = True

class KitchenOrderCreate(BaseModel):
    table_id: UUID
    items: List[KitchenOrderItemCreate]

class KitchenOrderResponse(BaseModel):
    id: UUID
    table_id: UUID
    status: KitchenOrderStatus
    created_at: datetime
    updated_at: datetime
    waiter_id: UUID
    items: List[KitchenOrderItemResponse] = []
    table_name: Optional[str] = None
    waiter_name: Optional[str] = None
    total_amount: Optional[float] = 0.0

    class Config:
        from_attributes = True

class KitchenOrderStatusUpdate(BaseModel):
    status: KitchenOrderStatus

# ═══════════════════════════════════════════════════════════════════════════════
#  POS v2 Schemas
# ═══════════════════════════════════════════════════════════════════════════════

# ── Table Zones ────────────────────────────────────────────────────────────────

class TableZoneCreate(BaseModel):
    name: str
    sort_order: int = 0

class TableZoneResponse(BaseModel):
    id: UUID
    name: str
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True

# ── POS Tables ─────────────────────────────────────────────────────────────────

class PosTableCreate(BaseModel):
    name: str
    zone_id: Optional[UUID] = None
    seats: int = 4
    sort_order: int = 0

class PosTableUpdate(BaseModel):
    name: Optional[str] = None
    zone_id: Optional[UUID] = None
    seats: Optional[int] = None
    status: Optional[TableStatus] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

class PosTableResponse(BaseModel):
    id: UUID
    name: str
    zone_id: Optional[UUID] = None
    seats: int
    status: TableStatus
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True

# ── Categories ─────────────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str
    color_hex: str = "#607D8B"
    icon_name: Optional[str] = None
    sort_order: int = 0

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    color_hex: Optional[str] = None
    icon_name: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

class CategoryResponse(BaseModel):
    id: int
    name: str
    color_hex: str
    icon_name: Optional[str] = None
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True

# ── Menu Items v2 ──────────────────────────────────────────────────────────────

class MenuItemCreateV2(BaseModel):
    name: str
    price: float
    category_id: int
    description: Optional[str] = None
    tax_rate: float = 0.23
    kitchen_print: bool = True
    bar_print: bool = False
    sort_order: int = 0

class MenuItemUpdateV2(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    category_id: Optional[int] = None
    description: Optional[str] = None
    tax_rate: Optional[float] = None
    kitchen_print: Optional[bool] = None
    bar_print: Optional[bool] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

class MenuItemResponseV2(BaseModel):
    id: UUID
    name: str
    price: float
    category_id: int
    description: Optional[str] = None
    tax_rate: float
    kitchen_print: bool
    bar_print: bool
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True

# ── Modifier Groups ────────────────────────────────────────────────────────────

class ModifierCreate(BaseModel):
    name: str
    price_override: float = 0.0
    sort_order: int = 0

class ModifierResponse(BaseModel):
    id: int
    group_id: int
    name: str
    price_override: float
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True

class ModifierGroupCreate(BaseModel):
    name: str
    min_select: int = 0
    max_select: int = 1
    modifiers: Optional[List[ModifierCreate]] = None

class ModifierGroupResponse(BaseModel):
    id: int
    name: str
    min_select: int
    max_select: int
    is_active: bool
    modifiers: List[ModifierResponse] = []

    class Config:
        from_attributes = True

# ── Orders ─────────────────────────────────────────────────────────────────────

class OrderItemCreate(BaseModel):
    menu_item_id: UUID
    quantity: int = 1
    course: int = 1
    notes: Optional[str] = None
    modifier_ids: List[int] = []

class OrderItemModifierResponse(BaseModel):
    id: UUID
    modifier_id: int
    modifier_name_snapshot: str
    price_snapshot: float

    class Config:
        from_attributes = True

class OrderItemResponse(BaseModel):
    id: UUID
    order_id: UUID
    menu_item_id: UUID
    quantity: int
    unit_price_snapshot: float
    item_name_snapshot: str
    course: int
    notes: Optional[str] = None
    kds_status: OrderItemKDSStatus
    sent_to_kitchen_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    split_tag: Optional[str] = None
    modifiers: List[OrderItemModifierResponse] = []

    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    table_id: UUID
    items: List[OrderItemCreate] = []
    guest_count: int = 1
    notes: Optional[str] = None

class OrderResponse(BaseModel):
    id: UUID
    table_id: UUID
    waiter_id: UUID
    status: OrderStatus
    guest_count: int
    notes: Optional[str] = None
    discount_pct: float
    created_at: datetime
    closed_at: Optional[datetime] = None
    items: List[OrderItemResponse] = []
    table_name: Optional[str] = None
    waiter_name: Optional[str] = None
    total_amount: Optional[float] = 0.0
    amount_paid: Optional[float] = 0.0
    amount_due: Optional[float] = 0.0

    @model_validator(mode='before')
    @classmethod
    def compute_totals(cls, data):
        """Compute total_amount, amount_paid, amount_due from order model."""
        try:
            items = data.items if not isinstance(data, dict) else data.get('items', [])
            payments = data.payments if not isinstance(data, dict) else data.get('payments', [])
            discount = data.discount_pct if not isinstance(data, dict) else data.get('discount_pct', 0)
            table = data.table if not isinstance(data, dict) else data.get('table')
            waiter = data.waiter if not isinstance(data, dict) else data.get('waiter')
        except AttributeError:
            return data

        # Calculate total from items
        subtotal = 0.0
        for item in (items or []):
            try:
                usp = item.unit_price_snapshot if not isinstance(item, dict) else item.get('unit_price_snapshot', 0)
                qty = item.quantity if not isinstance(item, dict) else item.get('quantity', 1)
                mods = item.modifiers if not isinstance(item, dict) else item.get('modifiers', [])
                mod_total = sum(
                    (m.price_snapshot if not isinstance(m, dict) else m.get('price_snapshot', 0))
                    for m in (mods or [])
                )
                subtotal += usp * qty + mod_total
            except (AttributeError, TypeError):
                pass

        discount_val = (discount or 0)
        total = subtotal * (1 - discount_val / 100)
        paid = sum(
            (p.amount if not isinstance(p, dict) else p.get('amount', 0))
            for p in (payments or [])
        )

        if isinstance(data, dict):
            data['total_amount'] = round(total, 2)
            data['amount_paid'] = round(paid, 2)
            data['amount_due'] = round(max(0, total - paid), 2)
            data['table_name'] = (table or {}).get('name') if isinstance(table, dict) else getattr(table, 'name', None)
            data['waiter_name'] = (waiter or {}).get('full_name') if isinstance(waiter, dict) else getattr(waiter, 'full_name', None)
        else:
            data.__dict__['total_amount'] = round(total, 2)
            data.__dict__['amount_paid'] = round(paid, 2)
            data.__dict__['amount_due'] = round(max(0, total - paid), 2)
            data.__dict__['table_name'] = getattr(table, 'name', None) if table else None
            data.__dict__['waiter_name'] = getattr(waiter, 'full_name', None) if waiter else None

        return data

    class Config:
        from_attributes = True

class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class OrderDiscountUpdate(BaseModel):
    discount_pct: float
    manager_pin: str

class OrderItemKDSStatusUpdate(BaseModel):
    kds_status: OrderItemKDSStatus

# ── Payments ───────────────────────────────────────────────────────────────────

class PaymentCreate(BaseModel):
    order_id: UUID
    method: PaymentMethod
    amount: float
    tip_amount: float = 0.0

class PaymentResponse(BaseModel):
    id: UUID
    order_id: UUID
    method: PaymentMethod
    amount: float
    tip_amount: float
    received_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# ── Tips ───────────────────────────────────────────────────────────────────────

class TipSummaryResponse(BaseModel):
    total_tips: float
    tip_count: int
    tips_by_method: dict = {}

# ── KDS Operations (v2 offline-sync) ───────────────────────────────────────────

class KDSSyncAction(BaseModel):
    """
    Represents a single state transition created by the client.
    """
    client_uuid: UUID
    order_item_id: UUID
    new_status: OrderItemKDSStatus
    client_timestamp: datetime
    is_undo: bool = False

    @field_validator('new_status')
    @classmethod
    def validate_monotonicity_client_side_hint(cls, v: OrderItemKDSStatus):
        # The true validation happens on the server against the DB state,
        # but basic checks can go here if needed.
        return v

class KDSSyncBatchPayload(BaseModel):
    """
    Payload for batch syncing offline actions from a KDS tablet.
    """
    actions: List[KDSSyncAction]
    last_sync_timestamp: Optional[datetime] = None

class KDSSyncResultItem(BaseModel):
    """
    Result of a single action in the sync process.
    """
    client_uuid: UUID
    success: bool
    error_code: Optional[str] = None
    server_timestamp: Optional[datetime] = None
    applied_status: Optional[OrderItemKDSStatus] = None

class KDSSyncResponse(BaseModel):
    """
    The full sync response returning the status of each uploaded action,
    plus the current state of active kitchen items.
    """
    results: List[KDSSyncResultItem]
    # Optionally, return the full state of the active kitchen queue so the tablet
    # can resync immediately if it was offline.
    refreshed_items: List[OrderItemResponse] = []
    server_time: datetime

