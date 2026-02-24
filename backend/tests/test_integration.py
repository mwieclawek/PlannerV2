"""
Integration Tests - Full E2E Workflow
Tests the complete user journey: manager setup → employee creation → schedule generation.
Uses the same in-memory async fixtures as other tests (conftest.py).

Run with: python -m pytest backend/tests/test_integration.py -v
"""
import pytest
import uuid
from datetime import date, timedelta
from sqlmodel import Session, select
from app.models import User, RoleSystem
from app.auth_utils import get_password_hash, create_access_token


# ── Helpers ────────────────────────────────────────────────────────────────────

def unique(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def make_user(session: Session, role: RoleSystem = RoleSystem.EMPLOYEE, password="TestPass123") -> User:
    """Insert a user directly into the in-memory test DB."""
    username = unique("user")
    user = User(
        username=username,
        full_name=f"Test {role.value.capitalize()}",
        password_hash=get_password_hash(password),
        role_system=role,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def auth_header(user: User) -> dict:
    token = create_access_token(data={"sub": user.username})
    return {"Authorization": f"Bearer {token}"}


# ── Full workflow ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_workflow(client, session: Session, manager_token_headers):
    """
    Step-by-step full workflow:
    1. Manager creates a job role
    2. Manager creates a shift definition
    3. Manager creates an employee account
    4. Manager assigns role to employee
    5. Employee sets their availability (AVAILABLE)
    6. Manager sets staffing requirements
    7. Manager triggers schedule generation
    8. Schedule is verified to include the employee
    """
    mgr_headers = manager_token_headers

    # ── Step 1: Create role ────────────────────────────────────────────────────
    role_name = unique("Role")
    r = await client.post("/manager/roles", headers=mgr_headers, json={
        "name": role_name, "color_hex": "#FF5733"
    })
    assert r.status_code == 200, f"Create role failed: {r.text}"
    role = r.json()
    role_id = role["id"]

    # ── Step 2: Create shift ───────────────────────────────────────────────────
    shift_name = unique("Shift")
    # Use random offset so parallel runs don't collide on time uniqueness
    hour = (uuid.uuid4().int % 10) + 1  # 01-10
    r = await client.post("/manager/shifts", headers=mgr_headers, json={
        "name": shift_name,
        "start_time": f"{hour:02d}:00",
        "end_time": f"{hour + 8:02d}:00",
    })
    assert r.status_code == 200, f"Create shift failed: {r.text}"
    shift = r.json()
    shift_id = shift["id"]

    # ── Step 3: Manager creates employee ──────────────────────────────────────
    emp_username = unique("emp")
    r = await client.post("/manager/users", headers=mgr_headers, json={
        "username": emp_username,
        "password": "EmpPass123",
        "full_name": "Integration Employee",
        "role_system": "EMPLOYEE",
    })
    assert r.status_code == 200, f"Create employee failed: {r.text}"
    emp_data = r.json()
    emp_id = emp_data["id"]

    # ── Step 4: Assign role to employee ───────────────────────────────────────
    r = await client.put(
        f"/manager/users/{emp_id}/roles",
        headers=mgr_headers,
        json={"role_ids": [role_id]},
    )
    assert r.status_code == 200, f"Assign role failed: {r.text}"

    # ── Step 5: Employee logs in and sets availability ─────────────────────────
    login_r = await client.post("/auth/token", data={
        "username": emp_username, "password": "EmpPass123"
    })
    assert login_r.status_code == 200
    emp_token = login_r.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    tomorrow = date.today() + timedelta(days=1)
    r = await client.post("/employee/availability", headers=emp_headers, json=[{
        "date": str(tomorrow),
        "shift_def_id": shift_id,
        "status": "AVAILABLE",
    }])
    assert r.status_code == 200, f"Set availability failed: {r.text}"

    # ── Step 6: Set staffing requirements ────────────────────────────────────
    r = await client.post("/manager/requirements", headers=mgr_headers, json=[{
        "date": str(tomorrow),
        "shift_def_id": shift_id,
        "role_id": role_id,
        "min_count": 1,
    }])
    assert r.status_code == 200, f"Set requirements failed: {r.text}"

    # ── Step 7: Generate schedule ─────────────────────────────────────────────
    r = await client.post("/scheduler/generate", headers=mgr_headers, json={
        "start_date": str(tomorrow),
        "end_date": str(tomorrow),
    })
    assert r.status_code == 200, f"Generate schedule failed: {r.text}"
    data = r.json()
    assert data["status"] == "success", f"Unexpected status: {data}"
    assert data["count"] >= 1, f"No assignments generated: {data}"

    # ── Step 8: Verify correct employee was assigned ──────────────────────────
    assignments = data["schedules"]
    my_assign = next((a for a in assignments if str(a["user_id"]) == str(emp_id)), None)
    assert my_assign is not None, (
        f"Employee {emp_id} not in assignments: {assignments}"
    )
    assert my_assign["shift_def_id"] == shift_id
    assert my_assign["role_id"] == role_id


@pytest.mark.asyncio
async def test_register_endpoint_disabled(client):
    """Registration endpoint must always return 403 (accounts created by manager only)."""
    r = await client.post("/auth/register", json={
        "username": unique("u"),
        "password": "TestPass123",
        "full_name": "Bob",
        "role_system": "EMPLOYEE",
    })
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_employee_cannot_access_manager_routes(client, employee_token_headers):
    """Employee must be blocked from manager-only endpoints."""
    r = await client.post("/manager/roles", headers=employee_token_headers, json={
        "name": "HackerRole", "color_hex": "#000000"
    })
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_login_refresh_token_flow(client, session: Session):
    """Login returns access+refresh token. Refresh endpoint yields a new access token."""
    user = make_user(session, RoleSystem.EMPLOYEE)

    # Login
    r = await client.post("/auth/token", data={
        "username": user.username, "password": "TestPass123"
    })
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body

    refresh_token = body["refresh_token"]

    # Refresh — yields a new access token
    r2 = await client.post("/auth/refresh", headers={
        "Authorization": f"Bearer {refresh_token}"
    })
    assert r2.status_code == 200, f"Refresh failed: {r2.text}"
    body2 = r2.json()
    assert "access_token" in body2

    # Verify the new access token actually works
    r3 = await client.get("/auth/me", headers={
        "Authorization": f"Bearer {body2['access_token']}"
    })
    assert r3.status_code == 200, f"/auth/me with new token failed: {r3.text}"
    assert r3.json()["username"] == user.username


@pytest.mark.asyncio
async def test_deactivated_user_cannot_login(client, session: Session):
    """Inactive users must be rejected at login."""
    user = make_user(session, RoleSystem.EMPLOYEE)
    user.is_active = False
    session.add(user)
    session.commit()

    r = await client.post("/auth/token", data={
        "username": user.username, "password": "TestPass123"
    })
    assert r.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
