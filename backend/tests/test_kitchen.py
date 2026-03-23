"""Tests for the POS & Kitchen Orders module."""
import pytest
from httpx import AsyncClient
from sqlmodel import Session

# ── 1. Tables ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_table_crud(client: AsyncClient, auth_headers: dict, employee_headers: dict):
    # Manager can create
    resp = await client.post("/kitchen/tables", json={"name": "Table 1", "is_active": True}, headers=auth_headers)
    assert resp.status_code == 201
    table_id = resp.json()["id"]

    # Employee cannot create
    resp_fail = await client.post("/kitchen/tables", json={"name": "Table 2", "is_active": True}, headers=employee_headers)
    assert resp_fail.status_code == 403

    # Waiter can list
    resp_list = await client.get("/kitchen/tables", headers=employee_headers)
    assert resp_list.status_code == 200
    assert len(resp_list.json()) >= 1

    # Manager can soft-delete
    resp_del = await client.delete(f"/kitchen/tables/{table_id}", headers=auth_headers)
    assert resp_del.status_code == 204

    # List without inactive
    resp_list2 = await client.get("/kitchen/tables", headers=employee_headers)
    table_ids = [t["id"] for t in resp_list2.json()]
    assert table_id not in table_ids  # Because include_inactive defaults to False

# ── 2. Menu ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_menu_crud(client: AsyncClient, auth_headers: dict, employee_headers: dict):
    payload = {
        "name": "Pizza Margherita",
        "price": 35.0,
        "category": "MAINS",
        "is_active": True
    }
    
    # Manager creates
    resp = await client.post("/kitchen/menu", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    item_id = resp.json()["id"]

    # Manager updates
    resp_up = await client.put(f"/kitchen/menu/{item_id}", json={"price": 40.0}, headers=auth_headers)
    assert resp_up.status_code == 200
    assert resp_up.json()["price"] == 40.0

    # Waiter lists
    resp_list = await client.get("/kitchen/menu?category=MAINS", headers=employee_headers)
    assert resp_list.status_code == 200
    assert len(resp_list.json()) >= 1

    # Employee cannot delete
    resp_del_fail = await client.delete(f"/kitchen/menu/{item_id}", headers=employee_headers)
    assert resp_del_fail.status_code == 403

    # Manager deletes (soft delete)
    resp_del = await client.delete(f"/kitchen/menu/{item_id}", headers=auth_headers)
    assert resp_del.status_code == 204

    # List without inactive
    resp_list2 = await client.get("/kitchen/menu?category=MAINS", headers=employee_headers)
    item_ids = [m["id"] for m in resp_list2.json()]
    assert item_id not in item_ids

# ── 3. POS Orders ──────────────────────────────────────────────────────────────

import pytest_asyncio

@pytest_asyncio.fixture
async def pos_setup_data(client: AsyncClient, auth_headers: dict):
    """Setup a table and a menu item to be used for orders."""
    # Create Table
    t_resp = await client.post("/kitchen/tables", json={"name": "Table X"}, headers=auth_headers)
    table_id = t_resp.json()["id"]

    # Create Menu Item
    m_resp = await client.post("/kitchen/menu", json={"name": "Burger", "price": 25.5, "category": "MAINS"}, headers=auth_headers)
    menu_item_id = m_resp.json()["id"]

    return {"table_id": table_id, "menu_item_id": menu_item_id}

@pytest.mark.asyncio
async def test_create_and_manage_order(client: AsyncClient, auth_headers: dict, employee_headers: dict, pos_setup_data):
    table_id = pos_setup_data["table_id"]
    menu_item_id = pos_setup_data["menu_item_id"]

    order_payload = {
        "table_id": table_id,
        "items": [
            {"menu_item_id": menu_item_id, "quantity": 2, "notes": "No pickles"}
        ]
    }

    # Waiter creates order
    resp = await client.post("/kitchen/orders", json=order_payload, headers=employee_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["table_id"] == table_id
    assert data["status"] == "PENDING"
    assert data["total_amount"] == 51.0  # 2 * 25.5
    assert len(data["items"]) == 1
    assert data["items"][0]["notes"] == "No pickles"
    assert data["items"][0]["unit_price"] == 25.5
    order_id = data["id"]

    # Waiter/Kitchen lists orders
    list_resp = await client.get("/kitchen/orders", headers=employee_headers)
    assert list_resp.status_code == 200
    assert any(o["id"] == order_id for o in list_resp.json())

    # Kitchen updates status to IN_PROGRESS
    patch_resp = await client.patch(f"/kitchen/orders/{order_id}/status", json={"status": "IN_PROGRESS"}, headers=employee_headers)
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "IN_PROGRESS"

    # Waiter cancels order
    cancel_resp = await client.delete(f"/kitchen/orders/{order_id}", headers=employee_headers)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"

@pytest.mark.asyncio
async def test_create_order_invalid_table(client: AsyncClient, employee_headers: dict, pos_setup_data):
    order_payload = {
        "table_id": "00000000-0000-0000-0000-000000000000",
        "items": [
            {"menu_item_id": pos_setup_data["menu_item_id"], "quantity": 1}
        ]
    }
    resp = await client.post("/kitchen/orders", json=order_payload, headers=employee_headers)
    assert resp.status_code == 400
