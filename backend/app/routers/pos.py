"""POS v2 Router – Full Antigravity POS API endpoints."""
from uuid import UUID
from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status

from sqlmodel import Session

from ..database import get_session
from ..auth_utils import get_current_user
from ..models import User, RoleSystem, TableStatus, OrderStatus, OrderItemKDSStatus
from ..schemas import (
    # Zones
    TableZoneCreate, TableZoneResponse,
    # Tables
    PosTableCreate, PosTableUpdate, PosTableResponse,
    # Categories
    CategoryCreate, CategoryUpdate, CategoryResponse,
    # Menu
    MenuItemCreateV2, MenuItemUpdateV2, MenuItemResponseV2,
    # Modifiers
    ModifierGroupCreate, ModifierGroupResponse,
    # Orders
    OrderCreate, OrderResponse, OrderStatusUpdate,
    OrderItemCreate, OrderItemResponse, OrderItemKDSStatusUpdate,
    OrderDiscountUpdate,
    # Payments
    PaymentCreate, PaymentResponse, TipSummaryResponse,
    # KDS Sync
    KDSSyncBatchPayload, KDSSyncResponse
)
from ..services.pos_service import PosService
from ..services.kds_service import KDSService

router = APIRouter(prefix="/pos/v2", tags=["pos-v2"])


def _get_pos_service(session: Session = Depends(get_session)) -> PosService:
    return PosService(session)


def _require_manager(user: User):
    if user.role_system != RoleSystem.MANAGER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Manager access required")


# ── 1. Table Zones ─────────────────────────────────────────────────────────────

@router.get("/zones", response_model=List[TableZoneResponse])
def list_zones(
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    return svc.list_zones()


@router.post("/zones", response_model=TableZoneResponse,
             status_code=status.HTTP_201_CREATED)
def create_zone(
    payload: TableZoneCreate,
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    _require_manager(current_user)
    return svc.create_zone(name=payload.name, sort_order=payload.sort_order)


# ── 2. POS Tables ──────────────────────────────────────────────────────────────

@router.get("/tables", response_model=List[PosTableResponse])
def list_tables(
    zone_id: Optional[UUID] = None,
    status_filter: Optional[TableStatus] = Query(default=None, alias="status"),
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    return svc.list_tables(zone_id=zone_id, status_filter=status_filter)


@router.post("/tables", response_model=PosTableResponse,
             status_code=status.HTTP_201_CREATED)
def create_table(
    payload: PosTableCreate,
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    _require_manager(current_user)
    return svc.create_table(
        name=payload.name, zone_id=payload.zone_id,
        seats=payload.seats, sort_order=payload.sort_order,
    )


@router.patch("/tables/{table_id}", response_model=PosTableResponse)
def update_table(
    table_id: UUID,
    payload: PosTableUpdate,
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    data = payload.model_dump(exclude_unset=True)
    return svc.update_table(table_id, **data)


# ── 3. Categories ──────────────────────────────────────────────────────────────

@router.get("/categories", response_model=List[CategoryResponse])
def list_categories(
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    return svc.list_categories()


@router.post("/categories", response_model=CategoryResponse,
             status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    _require_manager(current_user)
    return svc.create_category(
        name=payload.name, color_hex=payload.color_hex,
        icon_name=payload.icon_name, sort_order=payload.sort_order,
    )


@router.patch("/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    _require_manager(current_user)
    data = payload.model_dump(exclude_unset=True)
    return svc.update_category(category_id, **data)


# ── 4. Menu Items ──────────────────────────────────────────────────────────────

@router.get("/menu", response_model=List[MenuItemResponseV2])
def list_menu(
    category_id: Optional[int] = None,
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    return svc.list_menu_items(category_id=category_id)


@router.post("/menu", response_model=MenuItemResponseV2,
             status_code=status.HTTP_201_CREATED)
def create_menu_item(
    payload: MenuItemCreateV2,
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    _require_manager(current_user)
    data = payload.model_dump()
    return svc.create_menu_item(**data)


@router.patch("/menu/{item_id}", response_model=MenuItemResponseV2)
def update_menu_item(
    item_id: UUID,
    payload: MenuItemUpdateV2,
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    _require_manager(current_user)
    data = payload.model_dump(exclude_unset=True)
    return svc.update_menu_item(item_id, **data)


@router.post("/menu/{item_id}/modifier-groups/{group_id}",
             status_code=status.HTTP_204_NO_CONTENT)
def link_modifier_group(
    item_id: UUID,
    group_id: int,
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    _require_manager(current_user)
    svc.link_modifier_group(item_id, group_id)
    return None


# ── 5. Modifier Groups ────────────────────────────────────────────────────────

@router.get("/modifier-groups", response_model=List[ModifierGroupResponse])
def list_modifier_groups(
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    return svc.list_modifier_groups()


@router.post("/modifier-groups", response_model=ModifierGroupResponse,
             status_code=status.HTTP_201_CREATED)
def create_modifier_group(
    payload: ModifierGroupCreate,
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    _require_manager(current_user)
    modifiers = [m.model_dump() for m in payload.modifiers] if payload.modifiers else []
    return svc.create_modifier_group(
        name=payload.name,
        min_select=payload.min_select,
        max_select=payload.max_select,
        modifiers=modifiers,
    )


# ── 6. Orders ──────────────────────────────────────────────────────────────────

@router.post("/orders", response_model=OrderResponse,
             status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    items = [i.model_dump() for i in payload.items] if payload.items else []
    return svc.create_order(
        table_id=payload.table_id,
        waiter=current_user,
        items=items,
        guest_count=payload.guest_count,
        notes=payload.notes,
    )


@router.get("/orders", response_model=List[OrderResponse])
def list_orders(
    table_id: Optional[UUID] = None,
    status_filter: Optional[OrderStatus] = Query(default=None, alias="status"),
    waiter_id: Optional[UUID] = None,
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    return svc.list_orders(table_id=table_id, status_filter=status_filter,
                           waiter_id=waiter_id)


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: UUID,
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    return svc.get_order(order_id)


@router.post("/orders/{order_id}/items", response_model=OrderResponse)
def add_items_to_order(
    order_id: UUID,
    items: List[OrderItemCreate],
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    items_data = [i.model_dump() for i in items]
    return svc.add_items_to_order(order_id, items_data)


@router.patch("/orders/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: UUID,
    payload: OrderStatusUpdate,
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    return svc.update_order_status(order_id, payload.status)


@router.patch("/orders/{order_id}/discount", response_model=OrderResponse)
def apply_discount(
    order_id: UUID,
    payload: OrderDiscountUpdate,
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    return svc.apply_discount(order_id, payload.discount_pct,
                              payload.manager_pin)


# ── 7. KDS ─────────────────────────────────────────────────────────────────────

@router.patch("/order-items/{item_id}/kds-status",
              response_model=OrderItemResponse)
def update_item_kds_status(
    item_id: UUID,
    payload: OrderItemKDSStatusUpdate,
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    return svc.update_item_kds_status(item_id, payload.kds_status)


@router.get("/kds/items")
def list_kds_items(
    kds_status: Optional[OrderItemKDSStatus] = Query(default=None,
                                                      alias="status"),
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    items = svc.list_kds_items(status_filter=kds_status)
    # Apply pacing globally across the items returned
    # But pacing is calculated relative to courses within an order.
    # Group items by order, then apply pacing
    orders_map = {}
    for item in items:
        if item.order_id not in orders_map:
            orders_map[item.order_id] = []
        orders_map[item.order_id].append(item)
    
    pacing_metadata = {}
    for order_id, order_items in orders_map.items():
        pacing_metadata.update(KDSService.calculate_pacing(order_items))
        
    return {
        "items": [i.model_dump() for i in items],
        "pacing_metadata": pacing_metadata
    }

@router.post("/kds/sync", response_model=KDSSyncResponse)
def sync_kds_offline_batch(
    payload: KDSSyncBatchPayload,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Offline-first Sync endpoint for KDS tablets.
    Processes a list of operations monotonically, maintaining the audit trail
    and rejecting ghosts or stale updates.
    """
    result_dict = KDSService.process_sync_batch(session, payload, current_user)
    
    # Map the returned active items into proper response models
    orm_items = result_dict.get("refreshed_items_orm", [])
    response_items = []
    
    # Needs to handle modifier snapshots and such for OrderItemResponse
    # For now we'll do basic mapping assuming modifiers are eager loaded or not needed for active sync refreshed array
    # In a real scenario we'd use PosService mapping logic or identical query strategy
    
    return KDSSyncResponse(
        results=result_dict["results"],
        # Refreshed items omit full nested modifier evaluation for now to optimize sync payloads 
        # unless strictly queried. 
        refreshed_items=orm_items, 
        server_time=result_dict["server_time"]
    )

# ── 8. Payments ────────────────────────────────────────────────────────────────

@router.post("/payments", response_model=PaymentResponse,
             status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    return svc.create_payment(
        order_id=payload.order_id,
        method=payload.method,
        amount=payload.amount,
        tip_amount=payload.tip_amount,
        employee=current_user,
    )


# ── 9. Tips ────────────────────────────────────────────────────────────────────

@router.get("/tips/my", response_model=TipSummaryResponse)
def my_tips(
    target_date: Optional[date] = None,
    svc: PosService = Depends(_get_pos_service),
    current_user: User = Depends(get_current_user),
):
    return svc.get_tip_summary(current_user.id, target_date)
