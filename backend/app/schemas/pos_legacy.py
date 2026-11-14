from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from ..models import (
    TableStatus,
    OrderStatus,
    OrderItemKDSStatus,
    PaymentMethod,
    KitchenOrderStatus,
    MenuCategory,
)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


# ── Orders ─────────────────────────────────────────────────────────────────────

class OrderItemModifierCreate(BaseModel):
    modifier_id: int


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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


# ── DEPRECATED Legacy Schemas (kept for backward compat) ───────────────────────

class RestaurantTableCreate(BaseModel):
    name: str
    is_active: bool = True


class RestaurantTableResponse(BaseModel):
    id: UUID
    name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


class KitchenOrderStatusUpdate(BaseModel):
    status: KitchenOrderStatus
