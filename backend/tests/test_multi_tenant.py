import pytest
from httpx import AsyncClient
from sqlmodel import Session
from uuid import uuid4
from app.models import RestaurantConfig, User, RoleSystem, JobRole, ShiftDefinition
from app.auth_utils import get_password_hash, create_access_token
from datetime import time

@pytest.mark.asyncio
async def test_email_login_without_tenant_slug(client: AsyncClient, session: Session):
    """Users can log in using their email directly without providing a tenant slug."""
    rest = RestaurantConfig(name="Pizzeria Roma", slug="pizzeria-roma")
    session.add(rest)
    session.commit()
    session.refresh(rest)

    user = User(
        tenant_id=rest.id,
        username="mario",
        email="mario@roma.it",
        password_hash=get_password_hash("MarioPass1"),
        full_name="Mario Rossi",
        role_system=RoleSystem.MANAGER
    )
    session.add(user)
    session.commit()

    # Login with email (no X-Tenant-Slug header)
    response = await client.post(
        "/auth/token",
        data={"username": "mario@roma.it", "password": "MarioPass1"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

    # Verify /auth/me returns restaurant/tenant info
    me_resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "mario@roma.it"
    assert me_data["tenant_slug"] == "pizzeria-roma"
    assert me_data["tenant_name"] == "Pizzeria Roma"
    assert me_data["tenant_id"] == rest.id

@pytest.mark.asyncio
async def test_username_login_with_tenant_slug(client: AsyncClient, session: Session):
    """Users without email can log in with username and X-Tenant-Slug header."""
    rest = RestaurantConfig(name="Sushi Bar", slug="sushi-bar")
    session.add(rest)
    session.commit()
    session.refresh(rest)

    user = User(
        tenant_id=rest.id,
        username="kenji",
        email=None,  # No email on production
        password_hash=get_password_hash("KenjiPass1"),
        full_name="Kenji Sato",
        role_system=RoleSystem.EMPLOYEE
    )
    session.add(user)
    session.commit()

    # Login with username + X-Tenant-Slug
    response = await client.post(
        "/auth/token",
        data={"username": "kenji", "password": "KenjiPass1"},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Tenant-Slug": "sushi-bar"
        }
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]

    me_resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "kenji"
    assert me_resp.json()["tenant_slug"] == "sushi-bar"

@pytest.mark.asyncio
async def test_username_login_requires_tenant_slug_when_ambiguous(client: AsyncClient, session: Session):
    """When the same username exists in multiple restaurants, slug is required."""
    rest1 = RestaurantConfig(name="Bistro 1", slug="bistro-1")
    rest2 = RestaurantConfig(name="Bistro 2", slug="bistro-2")
    session.add_all([rest1, rest2])
    session.commit()
    session.refresh(rest1)
    session.refresh(rest2)

    user1 = User(
        tenant_id=rest1.id,
        username="jan",
        password_hash=get_password_hash("JanPass123"),
        full_name="Jan Kowalski 1",
        role_system=RoleSystem.EMPLOYEE
    )
    user2 = User(
        tenant_id=rest2.id,
        username="jan",
        password_hash=get_password_hash("JanPass123"),
        full_name="Jan Kowalski 2",
        role_system=RoleSystem.EMPLOYEE
    )
    session.add_all([user1, user2])
    session.commit()

    # Attempt login without tenant slug -> ambiguous -> 400
    response = await client.post(
        "/auth/token",
        data={"username": "jan", "password": "JanPass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 400
    assert "multiple restaurants" in response.json()["detail"]

@pytest.mark.asyncio
async def test_same_username_in_different_restaurants(client: AsyncClient, session: Session):
    """Two different restaurants can have employees with the same username."""
    rest1 = RestaurantConfig(name="Restauracja A", slug="rest-a")
    rest2 = RestaurantConfig(name="Restauracja B", slug="rest-b")
    session.add_all([rest1, rest2])
    session.commit()
    session.refresh(rest1)
    session.refresh(rest2)

    user1 = User(
        tenant_id=rest1.id,
        username="kelner",
        password_hash=get_password_hash("PassA1234"),
        full_name="Kelner A",
        role_system=RoleSystem.EMPLOYEE
    )
    user2 = User(
        tenant_id=rest2.id,
        username="kelner",
        password_hash=get_password_hash("PassB1234"),
        full_name="Kelner B",
        role_system=RoleSystem.EMPLOYEE
    )
    session.add_all([user1, user2])
    session.commit()

    # Login to Restaurant A
    resp_a = await client.post(
        "/auth/token",
        data={"username": "kelner", "password": "PassA1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded", "X-Tenant-Slug": "rest-a"}
    )
    assert resp_a.status_code == 200
    token_a = resp_a.json()["access_token"]
    me_a = await client.get("/auth/me", headers={"Authorization": f"Bearer {token_a}"})
    assert me_a.json()["full_name"] == "Kelner A"
    assert me_a.json()["tenant_slug"] == "rest-a"

    # Login to Restaurant B
    resp_b = await client.post(
        "/auth/token",
        data={"username": "kelner", "password": "PassB1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded", "X-Tenant-Slug": "rest-b"}
    )
    assert resp_b.status_code == 200
    token_b = resp_b.json()["access_token"]
    me_b = await client.get("/auth/me", headers={"Authorization": f"Bearer {token_b}"})
    assert me_b.json()["full_name"] == "Kelner B"
    assert me_b.json()["tenant_slug"] == "rest-b"

@pytest.mark.asyncio
async def test_tenant_data_isolation(client: AsyncClient, session: Session):
    """Data created in one restaurant is not visible to another restaurant."""
    rest1 = RestaurantConfig(name="Restauracja 1", slug="rest-1")
    rest2 = RestaurantConfig(name="Restauracja 2", slug="rest-2")
    session.add_all([rest1, rest2])
    session.commit()
    session.refresh(rest1)
    session.refresh(rest2)

    # Manager in rest1
    mgr1 = User(
        tenant_id=rest1.id,
        username="mgr1",
        email="mgr1@r1.com",
        password_hash=get_password_hash("MgrPass123"),
        full_name="Manager 1",
        role_system=RoleSystem.MANAGER
    )
    # Manager in rest2
    mgr2 = User(
        tenant_id=rest2.id,
        username="mgr2",
        email="mgr2@r2.com",
        password_hash=get_password_hash("MgrPass123"),
        full_name="Manager 2",
        role_system=RoleSystem.MANAGER
    )
    # Role only in rest1
    role1 = JobRole(tenant_id=rest1.id, name="Sommelier R1", color_hex="#123456")
    # Shift only in rest1
    shift1 = ShiftDefinition(tenant_id=rest1.id, name="Zmiana R1", start_time=time(9, 0), end_time=time(17, 0))

    session.add_all([mgr1, mgr2, role1, shift1])
    session.commit()

    token_mgr1 = create_access_token(data={"sub": mgr1.username, "tenant_id": str(rest1.id)})
    token_mgr2 = create_access_token(data={"sub": mgr2.username, "tenant_id": str(rest2.id)})

    # Manager 1 sees role1
    r1_roles = await client.get("/manager/roles", headers={"Authorization": f"Bearer {token_mgr1}"})
    assert r1_roles.status_code == 200
    assert any(r["name"] == "Sommelier R1" for r in r1_roles.json())

    # Manager 2 does NOT see role1
    r2_roles = await client.get("/manager/roles", headers={"Authorization": f"Bearer {token_mgr2}"})
    assert r2_roles.status_code == 200
    assert not any(r["name"] == "Sommelier R1" for r in r2_roles.json())

    # Manager 1 sees shift1
    r1_shifts = await client.get("/manager/shifts", headers={"Authorization": f"Bearer {token_mgr1}"})
    assert r1_shifts.status_code == 200
    assert any(s["name"] == "Zmiana R1" for s in r1_shifts.json())

    # Manager 2 does NOT see shift1
    r2_shifts = await client.get("/manager/shifts", headers={"Authorization": f"Bearer {token_mgr2}"})
    assert r2_shifts.status_code == 200
    assert not any(s["name"] == "Zmiana R1" for s in r2_shifts.json())
