"""POS v2 Service – Business logic for the Antigravity POS system."""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, date
from sqlmodel import Session, select, col
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

from ..models import (
    User, RoleSystem,
    TableZone, PosTable, TableStatus,
    Category, MenuItem, ModifierGroup, Modifier, MenuItemModifierGroup,
    Order, OrderItem, OrderItemModifier, OrderStatus, OrderItemKDSStatus,
    Payment, PaymentMethod,
)


class PosService:
    def __init__(self, session: Session):
        self.session = session

    # ── Table Zones ────────────────────────────────────────────────────────────

    def create_zone(self, name: str, sort_order: int = 0) -> TableZone:
        zone = TableZone(name=name, sort_order=sort_order)
        self.session.add(zone)
        self.session.commit()
        self.session.refresh(zone)
        logger.info(f"Created table zone: {zone.name} (ID: {zone.id})")
        return zone

    def list_zones(self, include_inactive: bool = False) -> List[TableZone]:
        stmt = select(TableZone).order_by(TableZone.sort_order)
        if not include_inactive:
            stmt = stmt.where(TableZone.is_active == True)
        return list(self.session.exec(stmt).all())

    # ── POS Tables ─────────────────────────────────────────────────────────────

    def create_table(self, name: str, zone_id: Optional[UUID] = None,
                     seats: int = 4, sort_order: int = 0) -> PosTable:
        if zone_id:
            zone = self.session.get(TableZone, zone_id)
            if not zone:
                raise HTTPException(status_code=404, detail="Zone not found")
        table = PosTable(name=name, zone_id=zone_id, seats=seats,
                         sort_order=sort_order)
        self.session.add(table)
        self.session.commit()
        self.session.refresh(table)
        logger.info(f"Created POS table: {table.name} (ID: {table.id})")
        return table

    def update_table(self, table_id: UUID, **kwargs) -> PosTable:
        table = self.session.get(PosTable, table_id)
        if not table:
            raise HTTPException(status_code=404, detail="Table not found")
        for key, value in kwargs.items():
            if value is not None:
                setattr(table, key, value)
        self.session.add(table)
        self.session.commit()
        self.session.refresh(table)
        return table

    def list_tables(self, zone_id: Optional[UUID] = None,
                    status_filter: Optional[TableStatus] = None,
                    include_inactive: bool = False) -> List[PosTable]:
        stmt = select(PosTable).order_by(PosTable.sort_order)
        if not include_inactive:
            stmt = stmt.where(PosTable.is_active == True)
        if zone_id:
            stmt = stmt.where(PosTable.zone_id == zone_id)
        if status_filter:
            stmt = stmt.where(PosTable.status == status_filter)
        return list(self.session.exec(stmt).all())

    # ── Categories ─────────────────────────────────────────────────────────────

    def create_category(self, name: str, color_hex: str = "#607D8B",
                        icon_name: Optional[str] = None,
                        sort_order: int = 0) -> Category:
        existing = self.session.exec(
            select(Category).where(Category.name == name)
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Category already exists")
        cat = Category(name=name, color_hex=color_hex, icon_name=icon_name,
                       sort_order=sort_order)
        self.session.add(cat)
        self.session.commit()
        self.session.refresh(cat)
        logger.info(f"Created category: {cat.name} (ID: {cat.id})")
        return cat

    def update_category(self, category_id: int, **kwargs) -> Category:
        cat = self.session.get(Category, category_id)
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")
        for key, value in kwargs.items():
            if value is not None:
                setattr(cat, key, value)
        self.session.add(cat)
        self.session.commit()
        self.session.refresh(cat)
        return cat

    def list_categories(self, include_inactive: bool = False) -> List[Category]:
        stmt = select(Category).order_by(Category.sort_order)
        if not include_inactive:
            stmt = stmt.where(Category.is_active == True)
        return list(self.session.exec(stmt).all())

    # ── Menu Items ─────────────────────────────────────────────────────────────

    def create_menu_item(self, **kwargs) -> MenuItem:
        cat = self.session.get(Category, kwargs.get("category_id"))
        if not cat:
            raise HTTPException(status_code=400, detail="Category not found")
        item = MenuItem(**kwargs)
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        logger.info(f"Created menu item: {item.name} (ID: {item.id})")
        return item

    def update_menu_item(self, item_id: UUID, **kwargs) -> MenuItem:
        item = self.session.get(MenuItem, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Menu item not found")
        for key, value in kwargs.items():
            if value is not None:
                setattr(item, key, value)
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def list_menu_items(self, category_id: Optional[int] = None,
                        include_inactive: bool = False) -> List[MenuItem]:
        stmt = select(MenuItem).order_by(MenuItem.sort_order)
        if not include_inactive:
            stmt = stmt.where(MenuItem.is_active == True)
        if category_id:
            stmt = stmt.where(MenuItem.category_id == category_id)
        return list(self.session.exec(stmt).all())

    def link_modifier_group(self, item_id: UUID, group_id: int) -> None:
        item = self.session.get(MenuItem, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Menu item not found")
        group = self.session.get(ModifierGroup, group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Modifier group not found")
        existing = self.session.exec(
            select(MenuItemModifierGroup).where(
                MenuItemModifierGroup.menu_item_id == item_id,
                MenuItemModifierGroup.modifier_group_id == group_id,
            )
        ).first()
        if existing:
            return  # already linked
        link = MenuItemModifierGroup(menu_item_id=item_id,
                                     modifier_group_id=group_id)
        self.session.add(link)
        self.session.commit()

    # ── Modifier Groups ────────────────────────────────────────────────────────

    def create_modifier_group(self, name: str, min_select: int = 0,
                              max_select: int = 1,
                              modifiers: Optional[List[dict]] = None) -> ModifierGroup:
        group = ModifierGroup(name=name, min_select=min_select,
                              max_select=max_select)
        self.session.add(group)
        self.session.flush()  # get group.id

        if modifiers:
            for idx, mod_data in enumerate(modifiers):
                mod = Modifier(
                    group_id=group.id,
                    name=mod_data["name"],
                    price_override=mod_data.get("price_override", 0.0),
                    sort_order=mod_data.get("sort_order", idx),
                )
                self.session.add(mod)

        self.session.commit()
        self.session.refresh(group)
        logger.info(f"Created modifier group: {group.name} (ID: {group.id})")
        return group

    def list_modifier_groups(self, include_inactive: bool = False) -> List[ModifierGroup]:
        stmt = select(ModifierGroup)
        if not include_inactive:
            stmt = stmt.where(ModifierGroup.is_active == True)
        return list(self.session.exec(stmt).all())

    # ── Orders ─────────────────────────────────────────────────────────────────

    def create_order(self, table_id: UUID, waiter: User,
                     items: List[dict], guest_count: int = 1,
                     notes: Optional[str] = None) -> Order:
        # Validate table
        table = self.session.get(PosTable, table_id)
        if not table or not table.is_active:
            raise HTTPException(status_code=400, detail="Table not found or inactive")

        order = Order(
            table_id=table_id,
            waiter_id=waiter.id,
            guest_count=guest_count,
            notes=notes,
        )
        self.session.add(order)
        self.session.flush()

        self._add_items_to_order(order, items)

        # Mark table as occupied
        table.status = TableStatus.OCCUPIED
        self.session.add(table)

        self.session.commit()
        self.session.refresh(order)
        logger.info(f"Created order {order.id} for table {table.name} by {waiter.full_name}")
        return self._load_order(order.id)

    def add_items_to_order(self, order_id: UUID, items: List[dict]) -> Order:
        order = self.session.get(Order, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status not in (OrderStatus.OPEN, OrderStatus.SENT):
            raise HTTPException(status_code=400,
                                detail="Cannot add items to a closed order")

        self._add_items_to_order(order, items)
        self.session.commit()
        return self._load_order(order_id)

    def _add_items_to_order(self, order: Order, items: List[dict]) -> None:
        """Snapshot prices/names and create OrderItems + OrderItemModifiers."""
        for item_data in items:
            menu_item = self.session.get(MenuItem, item_data["menu_item_id"])
            if not menu_item or not menu_item.is_active:
                raise HTTPException(
                    status_code=400,
                    detail=f"Menu item {item_data['menu_item_id']} not found or inactive"
                )

            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=menu_item.id,
                quantity=item_data.get("quantity", 1),
                unit_price_snapshot=menu_item.price,
                item_name_snapshot=menu_item.name,
                course=item_data.get("course", 1),
                notes=item_data.get("notes"),
            )
            self.session.add(order_item)
            self.session.flush()

            # Process modifiers
            for mod_id in item_data.get("modifier_ids", []):
                modifier = self.session.get(Modifier, mod_id)
                if not modifier:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Modifier {mod_id} not found"
                    )
                oim = OrderItemModifier(
                    order_item_id=order_item.id,
                    modifier_id=modifier.id,
                    modifier_name_snapshot=modifier.name,
                    price_snapshot=modifier.price_override,
                )
                self.session.add(oim)

    def get_order(self, order_id: UUID) -> Order:
        order = self._load_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    def list_orders(self, table_id: Optional[UUID] = None,
                    status_filter: Optional[OrderStatus] = None,
                    waiter_id: Optional[UUID] = None) -> List[Order]:
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.modifiers),
                selectinload(Order.payments),
                selectinload(Order.table),
                selectinload(Order.waiter),
            )
            .order_by(Order.created_at.desc())
        )
        if table_id:
            stmt = stmt.where(Order.table_id == table_id)
        if status_filter:
            stmt = stmt.where(Order.status == status_filter)
        if waiter_id:
            stmt = stmt.where(Order.waiter_id == waiter_id)
        return list(self.session.exec(stmt).all())

    def update_order_status(self, order_id: UUID, new_status: OrderStatus) -> Order:
        order = self.session.get(Order, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Validate transition
        _valid = {
            OrderStatus.OPEN: {OrderStatus.SENT, OrderStatus.CANCELLED},
            OrderStatus.SENT: {OrderStatus.PARTIALLY_PAID, OrderStatus.PAID, OrderStatus.CANCELLED},
            OrderStatus.PARTIALLY_PAID: {OrderStatus.PAID, OrderStatus.CANCELLED},
        }
        allowed = _valid.get(order.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition from {order.status.value} to {new_status.value}"
            )

        order.status = new_status
        if new_status in (OrderStatus.PAID, OrderStatus.CANCELLED):
            order.closed_at = datetime.utcnow()
            # Free the table
            table = self.session.get(PosTable, order.table_id)
            if table:
                # Only change to DIRTY if no other open orders on this table
                other_open = self.session.exec(
                    select(Order).where(
                        Order.table_id == order.table_id,
                        Order.id != order.id,
                        Order.status.in_([OrderStatus.OPEN, OrderStatus.SENT,
                                          OrderStatus.PARTIALLY_PAID])
                    )
                ).first()
                if not other_open:
                    table.status = TableStatus.DIRTY
                    self.session.add(table)

        self.session.add(order)
        self.session.commit()
        return self._load_order(order_id)

    def apply_discount(self, order_id: UUID, discount_pct: float,
                       manager_pin: str) -> Order:
        from ..auth_utils import verify_password
        order = self.session.get(Order, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Find a manager with matching PIN
        managers = self.session.exec(
            select(User).where(
                User.role_system == RoleSystem.MANAGER,
                User.manager_pin != None,
            )
        ).all()

        authorized_manager = None
        for mgr in managers:
            if mgr.manager_pin and verify_password(manager_pin, mgr.manager_pin):
                authorized_manager = mgr
                break

        if not authorized_manager:
            raise HTTPException(status_code=403, detail="Invalid manager PIN")

        if not 0 <= discount_pct <= 100:
            raise HTTPException(status_code=400, detail="Discount must be 0-100%")

        order.discount_pct = discount_pct
        order.discount_authorized_by = authorized_manager.id
        self.session.add(order)
        self.session.commit()
        logger.info(f"Discount {discount_pct}% applied to order {order_id} "
                     f"by manager {authorized_manager.full_name}")
        return self._load_order(order_id)

    # ── KDS ────────────────────────────────────────────────────────────────────

    def update_item_kds_status(self, item_id: UUID,
                               new_status: OrderItemKDSStatus) -> OrderItem:
        item = self.session.get(OrderItem, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Order item not found")

        item.kds_status = new_status
        now = datetime.utcnow()
        if new_status == OrderItemKDSStatus.PREPARING and not item.sent_to_kitchen_at:
            item.sent_to_kitchen_at = now
        elif new_status == OrderItemKDSStatus.READY:
            item.ready_at = now

        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def list_kds_items(self, status_filter: Optional[OrderItemKDSStatus] = None) -> List[dict]:
        """Return active KDS items grouped by order for the kitchen display."""
        stmt = (
            select(OrderItem)
            .join(Order)
            .where(Order.status.in_([OrderStatus.OPEN, OrderStatus.SENT]))
            .options(
                selectinload(OrderItem.modifiers),
                selectinload(OrderItem.order).selectinload(Order.table),
            )
            .order_by(OrderItem.sent_to_kitchen_at.asc())
        )
        if status_filter:
            stmt = stmt.where(OrderItem.kds_status == status_filter)
        else:
            stmt = stmt.where(
                OrderItem.kds_status.in_([
                    OrderItemKDSStatus.NEW,
                    OrderItemKDSStatus.PREPARING,
                    OrderItemKDSStatus.READY,
                ])
            )

        items = list(self.session.exec(stmt).all())

        # Group by order
        orders_map: dict[UUID, dict] = {}
        for item in items:
            oid = item.order_id
            if oid not in orders_map:
                orders_map[oid] = {
                    "order_id": oid,
                    "table_name": item.order.table.name if item.order and item.order.table else "?",
                    "created_at": item.order.created_at if item.order else None,
                    "items": [],
                }
            orders_map[oid]["items"].append(item)

        return list(orders_map.values())

    # ── Payments ───────────────────────────────────────────────────────────────

    def create_payment(self, order_id: UUID, method: PaymentMethod,
                       amount: float, tip_amount: float,
                       employee: User) -> Payment:
        order = self._load_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status in (OrderStatus.PAID, OrderStatus.CANCELLED):
            raise HTTPException(status_code=400,
                                detail="Order is already closed")

        payment = Payment(
            order_id=order_id,
            method=method,
            amount=amount,
            tip_amount=tip_amount,
            received_by=employee.id,
        )
        self.session.add(payment)

        # Recalculate: if fully paid → close order
        paid_so_far = sum(p.amount for p in order.payments) + amount
        if paid_so_far >= order.total_amount:
            order.status = OrderStatus.PAID
            order.closed_at = datetime.utcnow()
            # Set table to DIRTY
            table = self.session.get(PosTable, order.table_id)
            if table:
                other_open = self.session.exec(
                    select(Order).where(
                        Order.table_id == order.table_id,
                        Order.id != order.id,
                        Order.status.in_([OrderStatus.OPEN, OrderStatus.SENT,
                                          OrderStatus.PARTIALLY_PAID])
                    )
                ).first()
                if not other_open:
                    table.status = TableStatus.DIRTY
                    self.session.add(table)
        elif paid_so_far > 0 and order.status != OrderStatus.PARTIALLY_PAID:
            order.status = OrderStatus.PARTIALLY_PAID

        self.session.add(order)
        self.session.commit()
        self.session.refresh(payment)
        logger.info(f"Payment {payment.id}: {method.value} {amount} "
                     f"(tip: {tip_amount}) on order {order_id}")
        return payment

    def get_tip_summary(self, user_id: UUID,
                        target_date: Optional[date] = None) -> dict:
        """Smart Tips Tracker – today's tip totals for a waiter."""
        target = target_date or date.today()
        stmt = select(Payment).where(
            Payment.received_by == user_id,
            Payment.tip_amount > 0,
        )
        # Filter by date (created_at on same day)
        day_start = datetime(target.year, target.month, target.day, 0, 0, 0)
        day_end = datetime(target.year, target.month, target.day, 23, 59, 59)
        stmt = stmt.where(Payment.created_at >= day_start,
                          Payment.created_at <= day_end)

        payments = list(self.session.exec(stmt).all())

        tips_by_method: dict[str, float] = {}
        total = 0.0
        for p in payments:
            tips_by_method[p.method.value] = (
                tips_by_method.get(p.method.value, 0.0) + p.tip_amount
            )
            total += p.tip_amount

        return {
            "total_tips": round(total, 2),
            "tip_count": len(payments),
            "tips_by_method": tips_by_method,
        }

    # ── Helpers ─────────────────────────────────────────────────────────────────

    def _load_order(self, order_id: UUID) -> Optional[Order]:
        """Load an order with all relationships eagerly."""
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.items).selectinload(OrderItem.modifiers),
                selectinload(Order.payments),
                selectinload(Order.table),
                selectinload(Order.waiter),
            )
        )
        return self.session.exec(stmt).first()
