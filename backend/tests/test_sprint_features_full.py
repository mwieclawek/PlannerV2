import pytest
from datetime import date, time
from uuid import uuid4
from app.models import RestaurantConfig, User, RoleSystem, StaffingRequirement, ShiftDefinition, JobRole, AttendanceStatus
from app.auth_utils import create_access_token, get_password_hash

@pytest.fixture(name="manager_token")
def manager_token_fixture(session):
    user = User(
        username=f"mgr_{uuid4().hex[:8]}",
        password_hash=get_password_hash("secret"),
        full_name="Sprint Manager",
        role_system=RoleSystem.MANAGER
    )
    session.add(user)
    session.commit()
    token = create_access_token(data={"sub": user.username})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(name="test_user")
def test_user_fixture(session):
    user = User(
        username=f"emp_{uuid4().hex[:8]}",
        password_hash=get_password_hash("secret"),
        full_name="Employee One",
        role_system=RoleSystem.EMPLOYEE
    )
    session.add(user)
    session.commit()
    return user

@pytest.fixture(name="test_shift")
def test_shift_fixture(session):
    shift = ShiftDefinition(name="Morning", start_time=time(8, 0), end_time=time(16, 0))
    session.add(shift)
    session.commit()
    return shift

@pytest.fixture(name="test_role")
def test_role_fixture(session):
    role = JobRole(name="Cook", color_hex="#FF0000")
    session.add(role)
    session.commit()
    return role

class TestSprintFeatures:
    @pytest.mark.anyio
    async def test_partial_config_update(self, client, session, manager_token):
        # Setup initial config
        session.add(RestaurantConfig(id=1, name="Original"))
        session.commit()

        # Update only name
        resp = await client.post(
            "/manager/config",
            json={"name": "Updated Name"},
            headers=manager_token
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    @pytest.mark.anyio
    async def test_flexible_staffing_requirements(self, client, session, manager_token, test_shift, test_role):
        # 1. Set global requirement for Monday (0)
        resp = await client.post(
            "/manager/requirements",
            json=[{
                "day_of_week": 0,
                "shift_def_id": test_shift.id,
                "role_id": test_role.id,
                "min_count": 3
            }],
            headers=manager_token
        )
        if resp.status_code != 200:
            print(f"DEBUG: {resp.json()}")
        if resp.status_code != 200:
            print(f"DEBUG REQS: {resp.json()}")
        assert resp.status_code == 200

        # 2. Set specific date requirement for 2026-05-01
        resp = await client.post(
            "/manager/requirements",
            json=[{
                "date": "2026-05-01",
                "shift_def_id": test_shift.id,
                "role_id": test_role.id,
                "min_count": 5
            }],
            headers=manager_token
        )
        assert resp.status_code == 200
        assert resp.json()[0]["date"] == "2026-05-01"
        assert resp.json()[0]["min_count"] == 5

        # 3. Get combined requirements
        resp = await client.get(
            "/manager/requirements?start_date=2026-04-01&end_date=2026-05-31",
            headers=manager_token
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        # Verify both types exist in results
        types = { "global" if r.get("day_of_week") is not None else "specific" for r in data }
        assert "global" in types
        assert "specific" in types

    @pytest.mark.anyio
    async def test_user_monthly_preferences(self, client, session, manager_token, test_user):
        # Update user with monthly targets
        resp = await client.put(
            f"/manager/users/{test_user.id}",
            json={
                "target_hours_per_month": 160,
                "target_shifts_per_month": 22
            },
            headers=manager_token
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["target_hours_per_month"] == 160
        assert data["target_shifts_per_month"] == 22

    @pytest.mark.anyio
    async def test_manual_attendance_registration(self, client, session, manager_token, test_user):
        # Manually register attendance
        resp = await client.post(
            "/manager/attendance",
            json={
                "user_id": str(test_user.id),
                "date": "2026-02-10",
                "check_in": "08:30",
                "check_out": "17:00",
                "was_scheduled": False,
                "status": "CONFIRMED"
            },
            headers=manager_token
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["check_in"] == "08:30:00"
        assert data["user_name"] == "Employee One"
