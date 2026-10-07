"""
Seed test data for PlannerV2 with multi-tenant support.
Creates a default tenant and seeds all data within it.
"""
import uuid
from datetime import datetime, date, time, timedelta, timezone
from sqlalchemy import text
from sqlmodel import Session, create_engine, select
from app.models import (
    Tenant, User, RoleSystem, JobRole, UserJobRoleLink,
    ShiftDefinition, Schedule,
    TableZone, PosTable, TableStatus,
    Category, MenuItem, ModifierGroup, Modifier, MenuItemModifierGroup,
    Order, OrderStatus, OrderItem, OrderItemKDSStatus,
    RestaurantConfig, SystemSettings
)
from app.auth_utils import get_password_hash
from app.database import engine, init_db

def seed_data():
    init_db()
    with Session(engine) as session:
        print("Seeding database...")
        
        # Cleanup legacy column if alembic missed it
        try:
            session.execute(text("ALTER TABLE menuitem DROP COLUMN category"))
            session.commit()
        except Exception:
            pass
        
        # 0. Ensure default RestaurantConfig (Tenant) exists
        restaurant = session.exec(select(RestaurantConfig).where(RestaurantConfig.slug == "default")).first()
        if not restaurant:
            restaurant = RestaurantConfig(name="Default Restaurant", slug="default")
            session.add(restaurant)
            session.commit()
            session.refresh(restaurant)
        
        tenant_id = restaurant.id
        print(f"Using restaurant/tenant: {restaurant.name} (ID: {tenant_id})")
        
        # Ensure SystemSettings for this tenant
        settings = session.exec(select(SystemSettings).where(SystemSettings.tenant_id == tenant_id)).first()
        if not settings:
            settings = SystemSettings(tenant_id=tenant_id)
            session.add(settings)
            session.commit()
        
        # 1. Job Roles
        role_mgr = session.exec(select(JobRole).where(JobRole.name == "Manager", JobRole.tenant_id == tenant_id)).first()
        if not role_mgr:
            role_mgr = JobRole(tenant_id=tenant_id, name="Manager", color_hex="#F44336")
            session.add(role_mgr)
            
        role_kelner = session.exec(select(JobRole).where(JobRole.name == "Kelner", JobRole.tenant_id == tenant_id)).first()
        if not role_kelner:
            role_kelner = JobRole(tenant_id=tenant_id, name="Kelner", color_hex="#2196F3")
            session.add(role_kelner)
            
        role_kucharz = session.exec(select(JobRole).where(JobRole.name == "Kucharz", JobRole.tenant_id == tenant_id)).first()
        if not role_kucharz:
            role_kucharz = JobRole(tenant_id=tenant_id, name="Kucharz", color_hex="#4CAF50")
            session.add(role_kucharz)
        session.commit()

        # 2. Users
        def ensure_user(uname, passw, fname, lname, rsys, jrole, email=None):
            u = session.exec(select(User).where(User.username == uname, User.tenant_id == tenant_id)).first()
            if not u:
                u = User(
                    tenant_id=tenant_id,
                    username=uname,
                    email=email,
                    password_hash=get_password_hash(passw),
                    full_name=f"{fname} {lname}",
                    role_system=rsys,
                    is_active=True,
                    manager_pin=get_password_hash("1234") if rsys == RoleSystem.MANAGER else None
                )
                session.add(u)
                session.commit()
                # add job role link
                link = UserJobRoleLink(user_id=u.id, role_id=jrole.id)
                session.add(link)
                session.commit()
            return u

        u_mgr = ensure_user("manager", "Manager1", "Admin", "Manager", RoleSystem.MANAGER, role_mgr, "manager@default.pl")
        u_anna = ensure_user("anna", "Employee1", "Anna", "Nowak", RoleSystem.EMPLOYEE, role_kelner, "anna@default.pl")
        u_piotr = ensure_user("piotr", "Employee1", "Piotr", "Zarycki", RoleSystem.EMPLOYEE, role_kucharz, "piotr@default.pl")
        u_tomek = ensure_user("tomasz", "Employee1", "Tomasz", "Wiśniewski", RoleSystem.EMPLOYEE, role_kelner)

        # 3. Shift Definitions
        shift_rano = session.exec(select(ShiftDefinition).where(ShiftDefinition.name == "ZMIANA 1", ShiftDefinition.tenant_id == tenant_id)).first()
        if not shift_rano:
            shift_rano = ShiftDefinition(tenant_id=tenant_id, name="ZMIANA 1", start_time=time(8, 0), end_time=time(16, 0))
            session.add(shift_rano)
            
        shift_wieczor = session.exec(select(ShiftDefinition).where(ShiftDefinition.name == "ZMIANA 2", ShiftDefinition.tenant_id == tenant_id)).first()
        if not shift_wieczor:
            shift_wieczor = ShiftDefinition(tenant_id=tenant_id, name="ZMIANA 2", start_time=time(16, 0), end_time=time(23, 59))
            session.add(shift_wieczor)
        session.commit()

        # 4. Schedules (Grafiki for today and tomorrow)
        today = date.today()
        tomorrow = today + timedelta(days=1)
        # remove old schedules to avoid duplicates
        session.execute(text("DELETE FROM schedule"))
        
        session.add(Schedule(date=today, shift_def_id=shift_rano.id, user_id=u_anna.id, role_id=role_kelner.id))
        session.add(Schedule(date=today, shift_def_id=shift_rano.id, user_id=u_piotr.id, role_id=role_kucharz.id))
        session.add(Schedule(date=today, shift_def_id=shift_wieczor.id, user_id=u_tomek.id, role_id=role_kelner.id))
        
        session.add(Schedule(date=tomorrow, shift_def_id=shift_rano.id, user_id=u_tomek.id, role_id=role_kelner.id))
        session.add(Schedule(date=tomorrow, shift_def_id=shift_wieczor.id, user_id=u_anna.id, role_id=role_kelner.id))
        session.add(Schedule(date=tomorrow, shift_def_id=shift_wieczor.id, user_id=u_piotr.id, role_id=role_kucharz.id))
        session.commit()

        # 5. Table Zones
        zone_main = session.exec(select(TableZone).where(TableZone.name == "Sala Główna", TableZone.tenant_id == tenant_id)).first()
        if not zone_main:
            zone_main = TableZone(tenant_id=tenant_id, name="Sala Główna", sort_order=1)
            session.add(zone_main)
            
        zone_out = session.exec(select(TableZone).where(TableZone.name == "Ogródek", TableZone.tenant_id == tenant_id)).first()
        if not zone_out:
            zone_out = TableZone(tenant_id=tenant_id, name="Ogródek", sort_order=2)
            session.add(zone_out)
        session.commit()

        # 6. Tables
        if not session.exec(select(PosTable).where(PosTable.tenant_id == tenant_id)).first():
            for i in range(1, 6):
                session.add(PosTable(tenant_id=tenant_id, name=f"Stolik {i}", zone_id=zone_main.id, seats=4, sort_order=i))
            for i in range(6, 11):
                session.add(PosTable(tenant_id=tenant_id, name=f"Stolik zew. {i}", zone_id=zone_out.id, seats=2, sort_order=i))
            session.commit()

        # 7. Categories
        cat_przystawki = session.exec(select(Category).where(Category.name == "Przystawki", Category.tenant_id == tenant_id)).first()
        if not cat_przystawki:
            cat_przystawki = Category(tenant_id=tenant_id, name="Przystawki", color_hex="#E91E63", icon_name="tapas", sort_order=1)
            session.add(cat_przystawki)
            
        cat_dania = session.exec(select(Category).where(Category.name == "Dania Główne", Category.tenant_id == tenant_id)).first()
        if not cat_dania:
            cat_dania = Category(tenant_id=tenant_id, name="Dania Główne", color_hex="#FF9800", icon_name="restaurant", sort_order=2)
            session.add(cat_dania)
            
        cat_napoje = session.exec(select(Category).where(Category.name == "Napoje", Category.tenant_id == tenant_id)).first()
        if not cat_napoje:
            cat_napoje = Category(tenant_id=tenant_id, name="Napoje", color_hex="#03A9F4", icon_name="local_drink", sort_order=3)
            session.add(cat_napoje)
        session.commit()

        # 8. Modifiers (Stopień wysmażenia)
        mod_group = session.exec(select(ModifierGroup).where(ModifierGroup.name == "Stopień Wysmażenia", ModifierGroup.tenant_id == tenant_id)).first()
        if not mod_group:
            mod_group = ModifierGroup(tenant_id=tenant_id, name="Stopień Wysmażenia", min_select=1, max_select=1)
            session.add(mod_group)
            session.commit()
            session.add(Modifier(group_id=mod_group.id, name="Rare", price_override=0, sort_order=1))
            session.add(Modifier(group_id=mod_group.id, name="Medium", price_override=0, sort_order=2))
            session.add(Modifier(group_id=mod_group.id, name="Well Done", price_override=0, sort_order=3))
            session.commit()

        # 9. Menu Items
        if not session.exec(select(MenuItem).where(MenuItem.tenant_id == tenant_id)).first():
            item_tatar = MenuItem(tenant_id=tenant_id, name="Tatar Wołowy", price=45.0, category_id=cat_przystawki.id, prep_time_sec=300, sort_order=1)
            item_rosol = MenuItem(tenant_id=tenant_id, name="Rosół Królewski", price=25.0, category_id=cat_przystawki.id, prep_time_sec=120, sort_order=2)
            item_schab = MenuItem(tenant_id=tenant_id, name="Schabowy z Ziemniakami", price=49.0, category_id=cat_dania.id, prep_time_sec=900, sort_order=3)
            item_burger = MenuItem(tenant_id=tenant_id, name="Klasyczny Burger", price=55.0, category_id=cat_dania.id, prep_time_sec=600, sort_order=4)
            item_cola = MenuItem(tenant_id=tenant_id, name="Coca-Cola 0.3l", price=12.0, category_id=cat_napoje.id, kitchen_print=False, bar_print=True, sort_order=5)
            
            session.add_all([item_tatar, item_rosol, item_schab, item_burger, item_cola])
            session.commit()
            
            # Link modifier to burger
            session.add(MenuItemModifierGroup(menu_item_id=item_burger.id, modifier_group_id=mod_group.id))
            session.commit()
            
        # 10. Sample Order for KDS
        if not session.exec(select(Order)).first():
            table1 = session.exec(select(PosTable).where(PosTable.name == "Stolik 1")).first()
            now = datetime.now(timezone.utc)
            tatar = session.exec(select(MenuItem).where(MenuItem.name == "Tatar Wołowy")).first()
            burger = session.exec(select(MenuItem).where(MenuItem.name == "Klasyczny Burger")).first()
            
            order = Order(table_id=table1.id, waiter_id=u_anna.id, status=OrderStatus.SENT, guest_count=2, created_at=now)
            session.add(order)
            session.commit()
            
            oi1 = OrderItem(order_id=order.id, menu_item_id=tatar.id, quantity=1, unit_price_snapshot=tatar.price, item_name_snapshot=tatar.name, prep_time_sec_snapshot=tatar.prep_time_sec, course=1, kds_status=OrderItemKDSStatus.NEW)
            oi2 = OrderItem(order_id=order.id, menu_item_id=burger.id, quantity=1, unit_price_snapshot=burger.price, item_name_snapshot=burger.name, prep_time_sec_snapshot=burger.prep_time_sec, course=2, kds_status=OrderItemKDSStatus.NEW, notes="Bez pomidora")
            session.add_all([oi1, oi2])
            table1.status = TableStatus.OCCUPIED
            session.commit()
            
        print("Done seeding test data!")
        print(f"Default tenant/restaurant slug: '{restaurant.slug}'")
        print(f"Login: manager@default.pl / Manager1 (or username: manager + slug: default)")

if __name__ == '__main__':
    seed_data()
