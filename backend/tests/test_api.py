"""
Backend API Tests for PlannerV2
Uses in-memory SQLite via conftest.py fixtures — no live uvicorn needed.
Run with: pytest backend/tests/test_api.py -v
For Jenkins: pytest backend/tests/test_api.py --junitxml=test-results/backend-api.xml
"""
import pytest
import uuid
from datetime import date, timedelta, datetime
from sqlmodel import Session, select
from app.models import User, RoleSystem
from app.auth_utils import get_password_hash, create_access_token


# --- Test Data Helpers ---
def get_unique_username(prefix="user"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def get_employee_data():
    username = get_unique_username("employee")
    return {
        "username": username,
        "email": f"{username}@test.com",
        "password": "testpass123",
        "full_name": "Test Employee",
        "role_system": "EMPLOYEE"
    }


def create_user_in_db(session: Session, user_data: dict) -> User:
    """Insert user into test DB session"""
    existing = session.exec(
        select(User).where(User.username == user_data["username"])
    ).first()
    if existing:
        return existing

    user = User(
        username=user_data["username"],
        email=user_data.get("email"),
        full_name=user_data["full_name"],
        role_system=user_data["role_system"],
        password_hash=get_password_hash(user_data["password"]),
        created_at=datetime.utcnow(),
        is_active=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


class TestHealthCheck:
    """Basic connectivity tests"""

    @pytest.mark.asyncio
    async def test_api_reachable(self, client):
        response = await client.get("/docs")
        assert response.status_code == 200


class TestAuthentication:
    """Auth endpoint tests"""

    @pytest.mark.asyncio
    async def test_register_employee_disabled(self, client):
        """Registration should be disabled"""
        data = get_employee_data()
        response = await client.post("/auth/register", json=data)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_register_manager_fails(self, client):
        """Manager registration also disabled"""
        data = get_employee_data()
        data["role_system"] = "MANAGER"
        data["manager_pin"] = "1234"
        response = await client.post("/auth/register", json=data)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_login_success(self, client, session):
        manager_data = {
            "username": get_unique_username("mgr"),
            "email": "mgr_login@test.com",
            "password": "testpass123",
            "full_name": "Login Test Manager",
            "role_system": "MANAGER"
        }
        create_user_in_db(session, manager_data)

        response = await client.post("/auth/token", data={
            "username": manager_data["username"],
            "password": manager_data["password"]
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, session):
        manager_data = {
            "username": get_unique_username("mgr"),
            "email": "mgr_wrong@test.com",
            "password": "testpass123",
            "full_name": "Wrong Pass Manager",
            "role_system": "MANAGER"
        }
        create_user_in_db(session, manager_data)

        response = await client.post("/auth/token", data={
            "username": manager_data["username"],
            "password": "wrongpassword"
        })
        assert response.status_code == 401


class TestManagerEndpoints:
    """Manager-only endpoint tests"""

    @pytest.mark.asyncio
    async def test_create_role(self, client, auth_headers):
        response = await client.post("/manager/roles", headers=auth_headers, json={
            "name": f"Role {uuid.uuid4().hex[:4]}",
            "color_hex": "#FF0000"
        })
        assert response.status_code == 200
        assert "id" in response.json()

    @pytest.mark.asyncio
    async def test_create_shift(self, client, auth_headers):
        import random
        start_h = random.randint(0, 10)
        start_m = random.randint(0, 59)
        response = await client.post("/manager/shifts", headers=auth_headers, json={
            "name": f"Shift {uuid.uuid4().hex[:4]}",
            "start_time": f"{start_h:02d}:{start_m:02d}",
            "end_time": f"{start_h+8:02d}:{start_m:02d}"
        })
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_duplicate_shift_fails(self, client, auth_headers):
        s_h = 13
        name = f"Unique {uuid.uuid4().hex[:4]}"

        await client.post("/manager/shifts", headers=auth_headers, json={
            "name": name,
            "start_time": f"{s_h}:00",
            "end_time": f"{s_h+1}:00"
        })

        res_dup = await client.post("/manager/shifts", headers=auth_headers, json={
            "name": name + " Dup",
            "start_time": f"{s_h}:00",
            "end_time": f"{s_h+1}:00"
        })
        assert res_dup.status_code == 400
        assert "already exists" in res_dup.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_users_returns_created_at(self, client, session, auth_headers):
        """Regression test: /manager/users must return created_at field"""
        # /manager/users only returns EMPLOYEE role users, so create one first
        emp_data = get_employee_data()
        create_user_in_db(session, emp_data)

        response = await client.get("/manager/users", headers=auth_headers)
        assert response.status_code == 200
        users = response.json()
        assert len(users) > 0, "Should have at least one employee user"
        for user in users:
            assert "created_at" in user, f"User {user.get('id')} missing created_at field"
            assert "id" in user
            assert "email" in user
            assert "full_name" in user
            assert "role_system" in user
            assert "job_roles" in user


class TestSolverLogic:
    """Complex scenario: Setup data and verify solver generation"""

    @pytest.mark.asyncio
    async def test_full_generation_flow(self, client, session, auth_headers):
        # 1. Create Role
        role_resp = await client.post("/manager/roles", headers=auth_headers, json={
            "name": f"SolverRole_{uuid.uuid4().hex[:4]}",
            "color_hex": "#00FF00"
        })
        assert role_resp.status_code == 200
        role = role_resp.json()

        # 2. Create Shift
        shift_resp = await client.post("/manager/shifts", headers=auth_headers, json={
            "name": f"SolverShift_{uuid.uuid4().hex[:4]}",
            "start_time": "04:30",
            "end_time": "12:30"
        })
        if shift_resp.status_code == 400:  # Exists (time collision)
            all_shifts = (await client.get("/manager/shifts", headers=auth_headers)).json()
            shift = next(s for s in all_shifts if s["start_time"] == "04:30:00" and s["end_time"] == "12:30:00")
        else:
            assert shift_resp.status_code == 200
            shift = shift_resp.json()

        # 3. Create Employee in test DB
        emp_data = get_employee_data()
        create_user_in_db(session, emp_data)

        # 3.5 Login as employee
        emp_resp = await client.post("/auth/token", data={
            "username": emp_data["username"],
            "password": emp_data["password"]
        })
        assert emp_resp.status_code == 200
        emp_token = emp_resp.json()["access_token"]

        # Get employee ID
        emp_me = await client.get("/auth/me", headers={"Authorization": f"Bearer {emp_token}"})
        assert emp_me.status_code == 200
        emp_id = emp_me.json()["id"]

        # 4. Assign Role to Employee
        assign_resp = await client.put(
            f"/manager/users/{emp_id}/roles",
            headers=auth_headers,
            json={"role_ids": [role["id"]]}
        )
        assert assign_resp.status_code == 200

        # 5. Set Requirement (Need 1 person tomorrow)
        tomorrow = date.today() + timedelta(days=1)
        await client.post("/manager/requirements", headers=auth_headers, json=[{
            "date": str(tomorrow),
            "shift_def_id": shift["id"],
            "role_id": role["id"],
            "min_count": 1
        }])

        # 6. Set Availability
        await client.post(
            "/employee/availability",
            headers={"Authorization": f"Bearer {emp_token}"},
            json=[{
                "date": str(tomorrow),
                "shift_def_id": shift["id"],
                "status": "AVAILABLE"
            }]
        )

        # 7. Generate schedule
        res = await client.post("/scheduler/generate", headers=auth_headers, json={
            "start_date": str(tomorrow),
            "end_date": str(tomorrow)
        })

        assert res.status_code == 200
        data = res.json()

        assert data["status"] == "success"
        assert data["count"] >= 1

        assignments = data["schedules"]
        emp_id_str = str(emp_id)
        my_assignment = next(
            (a for a in assignments if str(a["user_id"]) == emp_id_str), None
        )

        assert my_assignment is not None, (
            f"No assignment found for emp_id={emp_id_str}. Assignments: {assignments}"
        )
        assert my_assignment["shift_def_id"] == shift["id"]
        assert my_assignment["role_id"] == role["id"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
