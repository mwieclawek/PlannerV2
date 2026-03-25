"""POS and Kitchen router – Tables, Menu, and Orders CRUD."""
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from ..database import get_session
from ..auth_utils import get_current_user
from ..models import (
    User, RoleSystem, RestaurantTable, MenuItem, MenuCategory,
    KitchenOrder, KitchenOrderItem, KitchenOrderStatus
)
from ..schemas import (
    RestaurantTableCreate, RestaurantTableResponse,
    MenuItemCreate, MenuItemUpdate, MenuItemResponse,
    KitchenOrderCreate, KitchenOrderResponse, KitchenOrderStatusUpdate
)

router = APIRouter(prefix="/kitchen", tags=["kitchen", "pos"])

# ── 1. Tables (Manager Only) ───────────────────────────────────────────────────

@router.get("/tables", response_model=List[RestaurantTableResponse])
def list_tables(
    include_inactive: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    stmt = select(RestaurantTable)
    if not include_inactive:
        stmt = stmt.where(RestaurantTable.is_active == True)
    return session.exec(stmt).all()

@router.post("/tables", response_model=RestaurantTableResponse, status_code=status.HTTP_201_CREATED)
def create_table(
    payload: RestaurantTableCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role_system != RoleSystem.MANAGER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only managers can manage tables")
    
    table = RestaurantTable(name=payload.name, is_active=payload.is_active)
    session.add(table)
    session.commit()
    session.refresh(table)
    return table

@router.delete("/tables/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_table(
    table_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role_system != RoleSystem.MANAGER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only managers can manage tables")
    
    table = session.get(RestaurantTable, table_id)
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    
    # Soft delete
    table.is_active = False
    session.add(table)
    session.commit()
    return None

# ── 2. Menu (Manager configures, Employees view) ───────────────────────────────

@router.get("/menu", response_model=List[MenuItemResponse])
def list_menu(
    category: Optional[MenuCategory] = None,
    include_inactive: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    stmt = select(MenuItem)
    if not include_inactive:
        stmt = stmt.where(MenuItem.is_active == True)
    if category:
        # Map legacy MenuCategory enum to new category_id
        _CATEGORY_MAP = {"SOUPS": 1, "MAINS": 2, "DESSERTS": 3, "DRINKS": 4}
        cat_id = _CATEGORY_MAP.get(category.value if hasattr(category, 'value') else category, None)
        if cat_id:
            stmt = stmt.where(MenuItem.category_id == cat_id)
    return session.exec(stmt).all()

@router.post("/menu", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
def create_menu_item(
    payload: MenuItemCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role_system != RoleSystem.MANAGER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only managers can manage menu")
    
    # Map legacy MenuCategory enum to new category_id
    _CATEGORY_MAP = {"SOUPS": 1, "MAINS": 2, "DESSERTS": 3, "DRINKS": 4}
    data = payload.model_dump() if hasattr(payload, 'model_dump') else payload.dict()
    cat_value = data.pop("category", None)
    if cat_value and "category_id" not in data:
        data["category_id"] = _CATEGORY_MAP.get(cat_value if isinstance(cat_value, str) else cat_value.value, 2)
    item = MenuItem(**data)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item

@router.put("/menu/{item_id}", response_model=MenuItemResponse)
def update_menu_item(
    item_id: UUID,
    payload: MenuItemUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role_system != RoleSystem.MANAGER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only managers can manage menu")
    
    item = session.get(MenuItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
    
    update_data = payload.model_dump(exclude_unset=True) if hasattr(payload, 'model_dump') else payload.dict(exclude_unset=True)
    # Map legacy category enum -> category_id
    if 'category' in update_data:
        _CATEGORY_MAP = {"SOUPS": 1, "MAINS": 2, "DESSERTS": 3, "DRINKS": 4}
        cat_val = update_data.pop('category')
        update_data['category_id'] = _CATEGORY_MAP.get(cat_val if isinstance(cat_val, str) else cat_val.value, 2)
    for key, value in update_data.items():
        setattr(item, key, value)
        
    session.add(item)
    session.commit()
    session.refresh(item)
    return item

@router.delete("/menu/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_menu_item(
    item_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role_system != RoleSystem.MANAGER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only managers can manage menu")
    
    item = session.get(MenuItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
    
    # Soft delete
    item.is_active = False
    session.add(item)
    session.commit()
    return None

# ── 3. Orders (POS & KDS) ──────────────────────────────────────────────────────

@router.post("/orders", response_model=KitchenOrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: KitchenOrderCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new kitchen order for a table (Waiters)."""
    # [WEBSOCKET FUTURE]: Broadcast NEW_ORDER event to all active KDS connections here
    # to avoid clients relying solely on 8-second HTTP polling.
    # Verify table
    table = session.get(RestaurantTable, payload.table_id)
    if not table or not table.is_active:
        raise HTTPException(status_code=400, detail="Table not found or inactive.")

    order = KitchenOrder(
        table_id=payload.table_id,
        waiter_id=current_user.id,
    )
    session.add(order)
    session.flush()  # to get order.id

    for item_data in payload.items:
        # Verify menu item & fetch current price
        menu_item = session.get(MenuItem, item_data.menu_item_id)
        if not menu_item or not menu_item.is_active:
             raise HTTPException(status_code=400, detail=f"Menu item {item_data.menu_item_id} not found or inactive")
             
        item = KitchenOrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            quantity=item_data.quantity,
            notes=item_data.notes,
            unit_price=menu_item.price, # Snapshot the price at order time
            menu_item_name_snapshot=menu_item.name, # Snapshot the name at order time
        )
        session.add(item)

    session.commit()
    session.refresh(order)
    return order


@router.get("/orders", response_model=List[KitchenOrderResponse])
def list_orders(
    table_id: Optional[UUID] = None,
    status_filter: Optional[KitchenOrderStatus] = Query(default=None, alias="status"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List orders, useful for Waiter screen or KDS (filtering by status)."""
    stmt = select(KitchenOrder)
    if table_id:
        stmt = stmt.where(KitchenOrder.table_id == table_id)
    if status_filter is not None:
        stmt = stmt.where(KitchenOrder.status == status_filter)
    
    stmt = stmt.order_by(KitchenOrder.created_at.desc())
    orders = session.exec(stmt).all()
    return orders


@router.get("/orders/{order_id}", response_model=KitchenOrderResponse)
def get_order(
    order_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    order = session.get(KitchenOrder, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.patch("/orders/{order_id}/status", response_model=KitchenOrderResponse)
def update_order_status(
    # [WEBSOCKET FUTURE]: Broadcast the order status change to active KDS connections here.
    # Ex: await manager.broadcast(f"Order {order_id} changed to {payload.status}")
    order_id: UUID,
    payload: KitchenOrderStatusUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update order status (from KDS: IN_PROGRESS -> READY, from POS: DELIVERED)."""
    order = session.get(KitchenOrder, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order.status = payload.status
    order.updated_at = datetime.utcnow()
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


@router.delete("/orders/{order_id}", response_model=KitchenOrderResponse)
def cancel_order(
    order_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Cancel a kitchen order (soft-delete)."""
    order = session.get(KitchenOrder, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.status in [KitchenOrderStatus.DELIVERED, KitchenOrderStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Order cannot be cancelled in current state")

    order.status = KitchenOrderStatus.CANCELLED
    order.updated_at = datetime.utcnow()
    session.add(order)
    session.commit()
    session.refresh(order)
    return order
