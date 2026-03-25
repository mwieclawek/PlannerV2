from uuid import UUID, uuid4
from datetime import datetime, date, timedelta, time, date as date_type
from typing import Optional, List
from enum import Enum
from pydantic import EmailStr, computed_field
from sqlmodel import SQLModel, Field, Relationship, col
from sqlalchemy import Column, Date, Integer

class RoleSystem(str, Enum):
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"

class AvailabilityStatus(str, Enum):
    UNAVAILABLE = "UNAVAILABLE"
    AVAILABLE = "AVAILABLE"

# Join table for User and JobRole
class UserJobRoleLink(SQLModel, table=True):
    user_id: Optional[UUID] = Field(default=None, foreign_key="user.id", primary_key=True)
    role_id: Optional[int] = Field(default=None, foreign_key="jobrole.id", primary_key=True)

class JobRole(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    color_hex: str
    
    users: List["User"] = Relationship(back_populates="job_roles", link_model=UserJobRoleLink)

class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: Optional[str] = Field(default=None)  # Optional, for contact only
    password_hash: str
    full_name: str
    role_system: RoleSystem = Field(default=RoleSystem.EMPLOYEE)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    target_hours_per_month: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))
    target_shifts_per_month: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))
    manager_pin: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    encrypted_google_access_token: Optional[str] = Field(default=None)
    encrypted_google_refresh_token: Optional[str] = Field(default=None)

    job_roles: List[JobRole] = Relationship(back_populates="users", link_model=UserJobRoleLink)
    availabilities: List["Availability"] = Relationship(back_populates="user")
    schedules: List["Schedule"] = Relationship(back_populates="user")
    devices: List["UserDevice"] = Relationship(back_populates="user")

    @property
    def google_access_token(self) -> Optional[str]:
        if not self.encrypted_google_access_token:
            return None
        import os
        from cryptography.fernet import Fernet
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            return self.encrypted_google_access_token
        try:
            f = Fernet(key.encode())
            return f.decrypt(self.encrypted_google_access_token.encode()).decode()
        except Exception:
            return self.encrypted_google_access_token

    @google_access_token.setter
    def google_access_token(self, value: Optional[str]):
        if not value:
            self.encrypted_google_access_token = None
            return
        import os
        from cryptography.fernet import Fernet
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            self.encrypted_google_access_token = value
            return
        f = Fernet(key.encode())
        self.encrypted_google_access_token = f.encrypt(value.encode()).decode()

    @property
    def google_refresh_token(self) -> Optional[str]:
        if not self.encrypted_google_refresh_token:
            return None
        import os
        from cryptography.fernet import Fernet
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            return self.encrypted_google_refresh_token
        try:
            f = Fernet(key.encode())
            return f.decrypt(self.encrypted_google_refresh_token.encode()).decode()
        except Exception:
            return self.encrypted_google_refresh_token

    @google_refresh_token.setter
    def google_refresh_token(self, value: Optional[str]):
        if not value:
            self.encrypted_google_refresh_token = None
            return
        import os
        from cryptography.fernet import Fernet
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            self.encrypted_google_refresh_token = value
            return
        f = Fernet(key.encode())
        self.encrypted_google_refresh_token = f.encrypt(value.encode()).decode()

class ShiftDefinitionDayLink(SQLModel, table=True):
    shift_def_id: Optional[int] = Field(default=None, foreign_key="shiftdefinition.id", primary_key=True)
    day_of_week: int = Field(primary_key=True)

class ShiftDefinition(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    start_time: time
    end_time: time
    days: List["ShiftDefinitionDayLink"] = Relationship()

class Availability(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    date: date
    shift_def_id: int = Field(foreign_key="shiftdefinition.id")
    status: AvailabilityStatus

    user: User = Relationship(back_populates="availabilities")

class StaffingRequirement(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    shift_def_id: int = Field(foreign_key="shiftdefinition.id")
    role_id: int = Field(foreign_key="jobrole.id")
    min_count: int
    date: Optional[date_type] = Field(default=None, sa_column=Column(Date, nullable=True))
    day_of_week: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))  # 0=Monday, 6=Sunday

class Schedule(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    date: date
    shift_def_id: int = Field(foreign_key="shiftdefinition.id")
    user_id: UUID = Field(foreign_key="user.id")
    role_id: int = Field(foreign_key="jobrole.id")
    is_published: bool = Field(default=False)


    user: User = Relationship(back_populates="schedules")

class RestaurantOpeningHour(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    config_id: int = Field(foreign_key="restaurantconfig.id")
    day_of_week: int
    open_time: time
    close_time: time

    config: "RestaurantConfig" = Relationship(back_populates="opening_hours")

class RestaurantConfig(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    name: str
    address: Optional[str] = None
    pos_enabled: bool = Field(default=False)
    
    opening_hours: List["RestaurantOpeningHour"] = Relationship(back_populates="config")

class AttendanceStatus(str, Enum):
    PENDING = "PENDING"       # Waiting for manager approval (unscheduled)
    CONFIRMED = "CONFIRMED"   # Confirmed attendance
    REJECTED = "REJECTED"     # Rejected by manager

class Attendance(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    date: date
    check_in: time
    check_out: time
    was_scheduled: bool = Field(default=True)  # Was this person scheduled that day?
    status: AttendanceStatus = Field(default=AttendanceStatus.CONFIRMED)
    schedule_id: Optional[UUID] = Field(default=None, foreign_key="schedule.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: User = Relationship()


class GiveawayStatus(str, Enum):
    OPEN = "OPEN"
    TAKEN = "TAKEN"
    CANCELLED = "CANCELLED"

class ShiftGiveaway(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    schedule_id: UUID = Field(foreign_key="schedule.id")
    offered_by: UUID = Field(foreign_key="user.id")
    status: GiveawayStatus = Field(default=GiveawayStatus.OPEN)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    taken_by: Optional[UUID] = Field(default=None, foreign_key="user.id")

    schedule: Schedule = Relationship()

class LeaveStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class LeaveRequest(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    start_date: date
    end_date: date
    reason: str = Field(max_length=500)
    status: LeaveStatus = Field(default=LeaveStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[UUID] = Field(default=None, foreign_key="user.id")

    user: User = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[LeaveRequest.user_id]"}
    )

class Notification(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    title: str = Field(max_length=200)
    body: str = Field(max_length=1000)
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserDevice(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    fcm_token: str = Field(unique=True, index=True)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    
    user: User = Relationship(back_populates="devices")


# ── POS & Kitchen (v2 – Production Schema) ─────────────────────────────────────

# ---------- Table / Floor Plan ----------

class TableZone(SQLModel, table=True):
    """A logical zone on the restaurant floor plan (e.g. Patio, Main Hall, Bar)."""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)

    tables: List["PosTable"] = Relationship(back_populates="zone")


class TableStatus(str, Enum):
    FREE = "FREE"
    OCCUPIED = "OCCUPIED"
    BILL_PRINTED = "BILL_PRINTED"
    DIRTY = "DIRTY"


class PosTable(SQLModel, table=True):
    """A physical table/seat in the restaurant."""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    zone_id: Optional[UUID] = Field(default=None, foreign_key="tablezone.id")
    seats: int = Field(default=4)
    status: TableStatus = Field(default=TableStatus.FREE)
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)

    zone: Optional[TableZone] = Relationship(back_populates="tables")
    orders: List["Order"] = Relationship(back_populates="table")


# ---------- Menu / Categories / Modifiers ----------

class Category(SQLModel, table=True):
    """Dynamic menu category (replaces the old MenuCategory enum)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    color_hex: str = Field(default="#607D8B")
    icon_name: Optional[str] = Field(default=None)
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)

    items: List["MenuItem"] = Relationship(back_populates="category_rel")


class MenuItem(SQLModel, table=True):
    """A product on the menu."""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    description: Optional[str] = Field(default=None)
    price: float = Field(default=0.0)
    category_id: int = Field(foreign_key="category.id")
    tax_rate: float = Field(default=0.23)
    prep_time_sec: int = Field(default=0)  # Pacing Engine: estimated preparation time
    kitchen_print: bool = Field(default=True)
    bar_print: bool = Field(default=False)
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)

    category_rel: Optional[Category] = Relationship(back_populates="items")
    modifier_groups: List["MenuItemModifierGroup"] = Relationship(
        back_populates="menu_item"
    )


class ModifierGroup(SQLModel, table=True):
    """A group of modifiers (e.g. 'Doneness', 'Extras')."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    min_select: int = Field(default=0)   # 0 = optional, 1+ = required
    max_select: int = Field(default=1)   # 1 = single-choice, N = multi
    is_active: bool = Field(default=True)

    modifiers: List["Modifier"] = Relationship(back_populates="group")
    menu_items: List["MenuItemModifierGroup"] = Relationship(
        back_populates="modifier_group"
    )


class Modifier(SQLModel, table=True):
    """A single modifier option (e.g. 'Medium rare', 'Extra cheese +5 PLN')."""
    id: Optional[int] = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="modifiergroup.id")
    name: str
    price_override: float = Field(default=0.0)
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)

    group: ModifierGroup = Relationship(back_populates="modifiers")


class MenuItemModifierGroup(SQLModel, table=True):
    """M2M join: which modifier groups apply to which menu items."""
    menu_item_id: Optional[UUID] = Field(
        default=None, foreign_key="menuitem.id", primary_key=True
    )
    modifier_group_id: Optional[int] = Field(
        default=None, foreign_key="modifiergroup.id", primary_key=True
    )

    menu_item: Optional[MenuItem] = Relationship(back_populates="modifier_groups")
    modifier_group: Optional[ModifierGroup] = Relationship(back_populates="menu_items")


# ---------- Orders ----------

class OrderStatus(str, Enum):
    OPEN = "OPEN"
    SENT = "SENT"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class OrderItemKDSStatus(str, Enum):
    """Monotonic states for KDS synchronisation (Weights: 10-99)."""
    NEW = "NEW"                           # 10
    ACKNOWLEDGED = "ACKNOWLEDGED"         # 20
    PREPARING = "PREPARING"               # 30
    READY = "READY"                       # 40
    DELIVERED = "DELIVERED"               # 50
    VOIDED_PENDING_ACK = "VOIDED_PENDING_ACK" # 98 (Anti-ghosting)
    VOIDED = "VOIDED"                     # 99 (Terminal)


class Order(SQLModel, table=True):
    """A POS order attached to a table and served by a waiter."""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    table_id: UUID = Field(foreign_key="postable.id")
    waiter_id: UUID = Field(foreign_key="user.id")
    status: OrderStatus = Field(default=OrderStatus.OPEN)
    guest_count: int = Field(default=1)
    notes: Optional[str] = Field(default=None)
    discount_pct: float = Field(default=0.0)
    discount_authorized_by: Optional[UUID] = Field(
        default=None, foreign_key="user.id"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = Field(default=None)

    table: Optional[PosTable] = Relationship(back_populates="orders")
    waiter: Optional[User] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Order.waiter_id]"}
    )
    items: List["OrderItem"] = Relationship(back_populates="order")
    payments: List["Payment"] = Relationship(back_populates="order")

    @computed_field
    @property
    def table_name(self) -> Optional[str]:
        return self.table.name if self.table else None

    @computed_field
    @property
    def waiter_name(self) -> Optional[str]:
        return self.waiter.full_name if self.waiter else None

    @computed_field
    @property
    def total_amount(self) -> float:
        """Gross total before discount (items + their modifiers)."""
        total = 0.0
        for item in self.items:
            item_total = item.unit_price_snapshot * item.quantity
            item_total += sum(m.price_snapshot for m in item.modifiers) * item.quantity
            total += item_total
        return round(total * (1 - self.discount_pct / 100), 2)

    @computed_field
    @property
    def amount_paid(self) -> float:
        return round(sum(p.amount for p in self.payments), 2)

    @computed_field
    @property
    def amount_due(self) -> float:
        return round(self.total_amount - self.amount_paid, 2)


class OrderItem(SQLModel, table=True):
    """A line-item on an order with immutable price/name snapshots."""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    order_id: UUID = Field(foreign_key="order.id")
    menu_item_id: UUID = Field(foreign_key="menuitem.id")
    quantity: int = Field(default=1)

    # ── Immutable snapshots (price history protection) ──
    unit_price_snapshot: float
    item_name_snapshot: str
    prep_time_sec_snapshot: int = Field(default=0)

    course: int = Field(default=1)
    notes: Optional[str] = Field(default=None)
    kds_status: OrderItemKDSStatus = Field(default=OrderItemKDSStatus.NEW)
    document_version: int = Field(default=1)  # Incremeted on modifications (Safety Lock)
    sent_to_kitchen_at: Optional[datetime] = Field(default=None)
    ready_at: Optional[datetime] = Field(default=None)
    split_tag: Optional[str] = Field(default=None)

    order: Order = Relationship(back_populates="items")
    menu_item: Optional[MenuItem] = Relationship()
    modifiers: List["OrderItemModifier"] = Relationship(back_populates="order_item")


class OrderItemModifier(SQLModel, table=True):
    """A modifier applied to an order item (with immutable snapshots)."""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    order_item_id: UUID = Field(foreign_key="orderitem.id")
    modifier_id: int = Field(foreign_key="modifier.id")

    # ── Snapshots ──
    modifier_name_snapshot: str
    price_snapshot: float = Field(default=0.0)

    order_item: OrderItem = Relationship(back_populates="modifiers")
    modifier: Optional[Modifier] = Relationship()


# ---------- Payments ----------

class PaymentMethod(str, Enum):
    CASH = "CASH"
    CARD = "CARD"
    VOUCHER = "VOUCHER"
    MOBILE = "MOBILE"


class Payment(SQLModel, table=True):
    """A single payment against an order (supports multi-method split)."""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    order_id: UUID = Field(foreign_key="order.id")
    method: PaymentMethod
    amount: float
    tip_amount: float = Field(default=0.0)
    received_by: UUID = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    order: Order = Relationship(back_populates="payments")
    employee: Optional[User] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Payment.received_by]"}
    )


# ---------- Audit Trail (KDS Logs) ----------

class KDSEventLog(SQLModel, table=True):
    """Immutable audit trail for every action/state change in KDS."""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    order_item_id: UUID = Field(foreign_key="orderitem.id", index=True)
    action_type: str  # e.g., "BUMP_TO_READY", "UNDO", "VOID_ACK"
    actor_id: Optional[UUID] = Field(default=None, foreign_key="user.id")
    old_state: Optional[str] = Field(default=None)
    new_state: str
    client_timestamp: datetime
    server_timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_undo: bool = Field(default=False)
    
    order_item: Optional[OrderItem] = Relationship()
    actor: Optional[User] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[KDSEventLog.actor_id]"}
    )


# ── DEPRECATED Legacy Aliases (kept for backward compat until frontend migration) ──
# The old RestaurantTable, KitchenOrder, KitchenOrderItem tables remain in the
# database but new code should use PosTable, Order, OrderItem above.

class MenuCategory(str, Enum):
    """DEPRECATED – use Category table instead."""
    SOUPS = "SOUPS"
    MAINS = "MAINS"
    DESSERTS = "DESSERTS"
    DRINKS = "DRINKS"

class KitchenOrderStatus(str, Enum):
    """DEPRECATED – use OrderItemKDSStatus instead."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    READY = "READY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class RestaurantTable(SQLModel, table=True):
    """DEPRECATED – use PosTable instead. Kept for existing migration/data."""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    is_active: bool = Field(default=True)

class KitchenOrder(SQLModel, table=True):
    """DEPRECATED – use Order instead."""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    table_id: UUID = Field(foreign_key="restauranttable.id")
    status: KitchenOrderStatus = Field(default=KitchenOrderStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    waiter_id: UUID = Field(foreign_key="user.id")

    items: List["KitchenOrderItem"] = Relationship(back_populates="order")
    table: Optional["RestaurantTable"] = Relationship()
    waiter: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[KitchenOrder.waiter_id]"}
    )

    @computed_field
    @property
    def table_name(self) -> Optional[str]:
        return self.table.name if self.table else None

    @computed_field
    @property
    def waiter_name(self) -> Optional[str]:
        return self.waiter.full_name if self.waiter else None

    @computed_field
    @property
    def total_amount(self) -> float:
        return sum(item.unit_price * item.quantity for item in self.items)

class KitchenOrderItem(SQLModel, table=True):
    """DEPRECATED – use OrderItem instead."""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    order_id: UUID = Field(foreign_key="kitchenorder.id")
    menu_item_id: UUID = Field(foreign_key="menuitem.id")
    quantity: int = Field(default=1)
    notes: Optional[str] = Field(default=None)
    unit_price: float = Field(default=0.0)
    menu_item_name_snapshot: Optional[str] = Field(default=None)

    order: KitchenOrder = Relationship(back_populates="items")
    menu_item: Optional["MenuItem"] = Relationship()

    @computed_field
    @property
    def menu_item_name(self) -> Optional[str]:
        return self.menu_item_name_snapshot or (self.menu_item.name if self.menu_item else None)
