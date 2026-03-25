"""Integration tests for the POS v2 API (/pos/v2/)."""
import pytest
from httpx import AsyncClient

# All tests use the conftest.py fixtures: session, client, auth_headers, employee_headers


# ── Helpers / Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture(name="pos_seed")
def pos_seed_fixture(session):
    """Seed categories so menu items can be created."""
    from app.models import Category
    cats = [
        Category(id=1, name="Zupy", color_hex="#FF7043", sort_order=1),
        Category(id=2, name="Dania główne", color_hex="#42A5F5", sort_order=2),
        Category(id=3, name="Desery", color_hex="#AB47BC", sort_order=3),
        Category(id=4, name="Napoje", color_hex="#66BB6A", sort_order=4),
    ]
    for c in cats:
        session.add(c)
    session.commit()
    return cats


# ── 1. Zone + Table CRUD ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_zone_and_table_crud(client: AsyncClient, auth_headers: dict, pos_seed):
    # Create zone
    resp = await client.post("/pos/v2/zones",
                             json={"name": "Taras", "sort_order": 1},
                             headers=auth_headers)
    assert resp.status_code == 201
    zone = resp.json()
    assert zone["name"] == "Taras"
    zone_id = zone["id"]

    # List zones
    resp = await client.get("/pos/v2/zones", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    # Create table in zone
    resp = await client.post("/pos/v2/tables",
                             json={"name": "T1", "zone_id": zone_id, "seats": 6},
                             headers=auth_headers)
    assert resp.status_code == 201
    table = resp.json()
    assert table["name"] == "T1"
    assert table["seats"] == 6
    assert table["status"] == "FREE"
    table_id = table["id"]

    # Update table status
    resp = await client.patch(f"/pos/v2/tables/{table_id}",
                              json={"status": "OCCUPIED"},
                              headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "OCCUPIED"

    # List tables by zone
    resp = await client.get(f"/pos/v2/tables?zone_id={zone_id}",
                            headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ── 2. Category CRUD ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_category_crud(client: AsyncClient, auth_headers: dict, pos_seed):
    # List seeded categories
    resp = await client.get("/pos/v2/categories", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 4

    # Create new category
    resp = await client.post("/pos/v2/categories",
                             json={"name": "Pizza", "color_hex": "#E53935"},
                             headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["name"] == "Pizza"

    # Duplicate name
    resp = await client.post("/pos/v2/categories",
                             json={"name": "Pizza"},
                             headers=auth_headers)
    assert resp.status_code == 400

    # Update category
    cat_id = resp.json()["detail"]  # error response
    resp_list = await client.get("/pos/v2/categories", headers=auth_headers)
    pizza = [c for c in resp_list.json() if c["name"] == "Pizza"][0]
    resp = await client.patch(f"/pos/v2/categories/{pizza['id']}",
                              json={"color_hex": "#D32F2F"},
                              headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["color_hex"] == "#D32F2F"


# ── 3. Menu Item + Modifiers ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_menu_item_and_modifiers(client: AsyncClient, auth_headers: dict, pos_seed):
    # Create menu item
    resp = await client.post("/pos/v2/menu",
                             json={"name": "Rosół", "price": 18.50, "category_id": 1},
                             headers=auth_headers)
    assert resp.status_code == 201
    item = resp.json()
    assert item["name"] == "Rosół"
    assert item["price"] == 18.50
    assert item["tax_rate"] == 0.23
    item_id = item["id"]

    # Create modifier group
    resp = await client.post("/pos/v2/modifier-groups",
                             json={
                                 "name": "Dodatki do zupy",
                                 "min_select": 0,
                                 "max_select": 3,
                                 "modifiers": [
                                     {"name": "Makaron", "price_override": 2.0},
                                     {"name": "Grzanki", "price_override": 3.0},
                                 ],
                             },
                             headers=auth_headers)
    assert resp.status_code == 201
    group = resp.json()
    assert len(group["modifiers"]) == 2
    group_id = group["id"]

    # Link modifier group to menu item
    resp = await client.post(
        f"/pos/v2/menu/{item_id}/modifier-groups/{group_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 204

    # Update menu item
    resp = await client.patch(f"/pos/v2/menu/{item_id}",
                              json={"price": 20.0},
                              headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["price"] == 20.0

    # List menu items by category
    resp = await client.get("/pos/v2/menu?category_id=1", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ── 4. Full Order Flow ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_order_flow(client: AsyncClient, auth_headers: dict, pos_seed):
    # Setup: create table + menu item
    resp = await client.post("/pos/v2/tables",
                             json={"name": "Stolik 5", "seats": 4},
                             headers=auth_headers)
    table_id = resp.json()["id"]

    resp = await client.post("/pos/v2/menu",
                             json={"name": "Kotlet", "price": 35.0, "category_id": 2},
                             headers=auth_headers)
    item_id = resp.json()["id"]

    resp = await client.post("/pos/v2/menu",
                             json={"name": "Piwo", "price": 12.0, "category_id": 4},
                             headers=auth_headers)
    drink_id = resp.json()["id"]

    # Create order with items
    resp = await client.post("/pos/v2/orders",
                             json={
                                 "table_id": table_id,
                                 "guest_count": 2,
                                 "items": [
                                     {"menu_item_id": item_id, "quantity": 2, "course": 1},
                                     {"menu_item_id": drink_id, "quantity": 3, "course": 1,
                                      "notes": "Zimne!"},
                                 ],
                             },
                             headers=auth_headers)
    assert resp.status_code == 201
    order = resp.json()
    assert order["status"] == "OPEN"
    assert order["guest_count"] == 2
    assert len(order["items"]) == 2
    order_id = order["id"]

    # Verify snapshots
    kotlet_item = [i for i in order["items"] if i["item_name_snapshot"] == "Kotlet"][0]
    assert kotlet_item["unit_price_snapshot"] == 35.0
    assert kotlet_item["quantity"] == 2

    # Table should now be OCCUPIED
    resp = await client.get(f"/pos/v2/tables", headers=auth_headers)
    table_data = [t for t in resp.json() if t["id"] == table_id][0]
    assert table_data["status"] == "OCCUPIED"

    # Add more items to order
    resp = await client.post(f"/pos/v2/orders/{order_id}/items",
                             json=[{"menu_item_id": drink_id, "quantity": 1}],
                             headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 3

    # Send order
    resp = await client.patch(f"/pos/v2/orders/{order_id}/status",
                              json={"status": "SENT"},
                              headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "SENT"

    # Get single order
    resp = await client.get(f"/pos/v2/orders/{order_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == order_id


# ── 5. KDS Item Status ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_kds_item_status(client: AsyncClient, auth_headers: dict, pos_seed):
    # Setup: table + item + order
    resp = await client.post("/pos/v2/tables",
                             json={"name": "KDS Table"},
                             headers=auth_headers)
    table_id = resp.json()["id"]

    resp = await client.post("/pos/v2/menu",
                             json={"name": "Sałatka", "price": 22.0, "category_id": 2},
                             headers=auth_headers)
    item_id = resp.json()["id"]

    resp = await client.post("/pos/v2/orders",
                             json={"table_id": table_id,
                                   "items": [{"menu_item_id": item_id}]},
                             headers=auth_headers)
    order = resp.json()
    oi_id = order["items"][0]["id"]

    # Item starts NEW
    assert order["items"][0]["kds_status"] == "NEW"

    # Move to PREPARING
    resp = await client.patch(f"/pos/v2/order-items/{oi_id}/kds-status",
                              json={"kds_status": "PREPARING"},
                              headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["kds_status"] == "PREPARING"
    assert resp.json()["sent_to_kitchen_at"] is not None

    # Move to READY
    resp = await client.patch(f"/pos/v2/order-items/{oi_id}/kds-status",
                              json={"kds_status": "READY"},
                              headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["kds_status"] == "READY"
    assert resp.json()["ready_at"] is not None

    # KDS list
    resp = await client.get("/pos/v2/kds/items", headers=auth_headers)
    assert resp.status_code == 200


# ── 6. Payment + Tip ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_payment_and_tips(client: AsyncClient, auth_headers: dict, pos_seed):
    # Setup order
    resp = await client.post("/pos/v2/tables",
                             json={"name": "Pay Table"},
                             headers=auth_headers)
    table_id = resp.json()["id"]

    resp = await client.post("/pos/v2/menu",
                             json={"name": "Steak", "price": 65.0, "category_id": 2},
                             headers=auth_headers)
    item_id = resp.json()["id"]

    resp = await client.post("/pos/v2/orders",
                             json={"table_id": table_id,
                                   "items": [{"menu_item_id": item_id, "quantity": 1}]},
                             headers=auth_headers)
    order = resp.json()
    order_id = order["id"]

    # Send order first
    await client.patch(f"/pos/v2/orders/{order_id}/status",
                       json={"status": "SENT"}, headers=auth_headers)

    # Partial payment (split bill)
    resp = await client.post("/pos/v2/payments",
                             json={"order_id": order_id, "method": "CARD",
                                   "amount": 30.0, "tip_amount": 5.0},
                             headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["tip_amount"] == 5.0

    # Check order is now PARTIALLY_PAID
    resp = await client.get(f"/pos/v2/orders/{order_id}", headers=auth_headers)
    assert resp.json()["status"] == "PARTIALLY_PAID"

    # Pay the rest
    resp = await client.post("/pos/v2/payments",
                             json={"order_id": order_id, "method": "CASH",
                                   "amount": 35.0, "tip_amount": 3.0},
                             headers=auth_headers)
    assert resp.status_code == 201

    # Check order is PAID
    resp = await client.get(f"/pos/v2/orders/{order_id}", headers=auth_headers)
    assert resp.json()["status"] == "PAID"
    assert resp.json()["closed_at"] is not None

    # Table should be DIRTY now
    resp = await client.get("/pos/v2/tables", headers=auth_headers)
    table = [t for t in resp.json() if t["id"] == table_id][0]
    assert table["status"] == "DIRTY"

    # Smart Tips Tracker
    resp = await client.get("/pos/v2/tips/my", headers=auth_headers)
    assert resp.status_code == 200
    tips = resp.json()
    assert tips["total_tips"] == 8.0
    assert tips["tip_count"] == 2
    assert "CARD" in tips["tips_by_method"]
    assert "CASH" in tips["tips_by_method"]


# ── 7. Employee access control ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_employee_cannot_create_category(
    client: AsyncClient, employee_headers: dict, pos_seed
):
    resp = await client.post("/pos/v2/categories",
                             json={"name": "Nope"},
                             headers=employee_headers)
    assert resp.status_code == 403


# ── 8. Invalid transitions ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invalid_order_status_transition(
    client: AsyncClient, auth_headers: dict, pos_seed
):
    # Setup order
    resp = await client.post("/pos/v2/tables",
                             json={"name": "Trans Table"},
                             headers=auth_headers)
    table_id = resp.json()["id"]

    resp = await client.post("/pos/v2/menu",
                             json={"name": "Burger", "price": 28.0, "category_id": 2},
                             headers=auth_headers)
    item_id = resp.json()["id"]

    resp = await client.post("/pos/v2/orders",
                             json={"table_id": table_id,
                                   "items": [{"menu_item_id": item_id}]},
                             headers=auth_headers)
    order_id = resp.json()["id"]

    # OPEN → PAID should fail (must go through SENT first)
    resp = await client.patch(f"/pos/v2/orders/{order_id}/status",
                              json={"status": "PAID"},
                              headers=auth_headers)
    assert resp.status_code == 400
