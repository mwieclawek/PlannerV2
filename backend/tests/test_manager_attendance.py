"""
Tests for new manager attendance and employee-hours endpoints.
Run with: pytest backend/tests/test_manager_attendance.py -v
"""
import pytest
from datetime import date, time, timedelta
from uuid import uuid4

from app.models import (
    User, RoleSystem, Attendance, AttendanceStatus,
    Schedule, ShiftDefinition, JobRole, Availability, AvailabilityStatus
)
from app.auth_utils import get_password_hash, create_access_token


# ---- Fixtures ----

@pytest.fixture(name="manager_with_token")
def manager_with_token_fixture(session):
    """Create a manager and return (user, auth_headers)"""
    user = User(
        username=f"mgr_{uuid4().hex[:8]}",
        password_hash=get_password_hash("secret"),
        full_name="Test Manager",
        role_system=RoleSystem.MANAGER
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    token = create_access_token(data={"sub": user.username})
    return user, {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="employee")
def employee_fixture(session):
    """Create an employee"""
    user = User(
        username=f"emp_{uuid4().hex[:8]}",
        password_hash=get_password_hash("secret"),
        full_name="Test Employee",
        role_system=RoleSystem.EMPLOYEE
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="employee2")
def employee2_fixture(session):
    """Create a second employee"""
    user = User(
        username=f"emp2_{uuid4().hex[:8]}",
        password_hash=get_password_hash("secret"),
        full_name="Second Employee",
        role_system=RoleSystem.EMPLOYEE
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="test_shift")
def test_shift_fixture(session):
    """Create a shift definition (8h shift)"""
    shift = ShiftDefinition(
        name="Test Morning",
        start_time=time(8, 0),
        end_time=time(16, 0)
    )
    session.add(shift)
    session.commit()
    session.refresh(shift)
    return shift


@pytest.fixture(name="test_role")
def test_role_fixture(session):
    """Create a job role"""
    role = JobRole(name="TestRole", color_hex="#FF0000")
    session.add(role)
    session.commit()
    session.refresh(role)
    return role


# ---- GET /manager/attendance ----

class TestGetAllAttendance:
    """Tests for GET /manager/attendance endpoint"""

    @pytest.mark.anyio
    async def test_empty_returns_empty_list(self, client, manager_with_token):
        _, headers = manager_with_token
        resp = await client.get(
            "/manager/attendance",
            params={"start_date": "2026-02-01", "end_date": "2026-02-28"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_returns_all_statuses(self, client, session, manager_with_token, employee):
        _, headers = manager_with_token
        # Create attendance records with different statuses
        for status in [AttendanceStatus.PENDING, AttendanceStatus.CONFIRMED, AttendanceStatus.REJECTED]:
            a = Attendance(
                user_id=employee.id,
                date=date(2026, 2, 10),
                check_in=time(8, 0),
                check_out=time(16, 0),
                was_scheduled=True,
                status=status,
            )
            session.add(a)
        session.commit()

        resp = await client.get(
            "/manager/attendance",
            params={"start_date": "2026-02-01", "end_date": "2026-02-28"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        statuses = {r["status"] for r in data}
        assert statuses == {"PENDING", "CONFIRMED", "REJECTED"}

    @pytest.mark.anyio
    async def test_filter_by_status(self, client, session, manager_with_token, employee):
        _, headers = manager_with_token
        # Create one CONFIRMED and one PENDING
        session.add(Attendance(
            user_id=employee.id, date=date(2026, 3, 1),
            check_in=time(8, 0), check_out=time(16, 0),
            was_scheduled=True, status=AttendanceStatus.CONFIRMED,
        ))
        session.add(Attendance(
            user_id=employee.id, date=date(2026, 3, 2),
            check_in=time(9, 0), check_out=time(17, 0),
            was_scheduled=False, status=AttendanceStatus.PENDING,
        ))
        session.commit()

        resp = await client.get(
            "/manager/attendance",
            params={"start_date": "2026-03-01", "end_date": "2026-03-31", "status": "CONFIRMED"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "CONFIRMED"

    @pytest.mark.anyio
    async def test_invalid_status_returns_400(self, client, manager_with_token):
        _, headers = manager_with_token
        resp = await client.get(
            "/manager/attendance",
            params={"start_date": "2026-02-01", "end_date": "2026-02-28", "status": "INVALID"},
            headers=headers,
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_date_range_filtering(self, client, session, manager_with_token, employee):
        _, headers = manager_with_token
        # Record INSIDE range
        session.add(Attendance(
            user_id=employee.id, date=date(2026, 4, 15),
            check_in=time(8, 0), check_out=time(16, 0),
            was_scheduled=True, status=AttendanceStatus.CONFIRMED,
        ))
        # Record OUTSIDE range
        session.add(Attendance(
            user_id=employee.id, date=date(2026, 5, 1),
            check_in=time(8, 0), check_out=time(16, 0),
            was_scheduled=True, status=AttendanceStatus.CONFIRMED,
        ))
        session.commit()

        resp = await client.get(
            "/manager/attendance",
            params={"start_date": "2026-04-01", "end_date": "2026-04-30"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["date"] == "2026-04-15"

    @pytest.mark.anyio
    async def test_response_fields_complete(self, client, session, manager_with_token, employee):
        _, headers = manager_with_token
        session.add(Attendance(
            user_id=employee.id, date=date(2026, 6, 10),
            check_in=time(9, 30), check_out=time(17, 45),
            was_scheduled=False, status=AttendanceStatus.PENDING,
        ))
        session.commit()

        resp = await client.get(
            "/manager/attendance",
            params={"start_date": "2026-06-01", "end_date": "2026-06-30"},
            headers=headers,
        )
        assert resp.status_code == 200
        record = resp.json()[0]
        assert "id" in record
        assert "user_id" in record
        assert record["user_name"] == "Test Employee"
        assert record["check_in"] == "09:30"
        assert record["check_out"] == "17:45"
        assert record["was_scheduled"] is False
        assert record["status"] == "PENDING"


# ---- GET /manager/employee-hours ----

class TestEmployeeHours:
    """Tests for GET /manager/employee-hours endpoint"""

    @pytest.mark.anyio
    async def test_empty_schedule_returns_zero_hours(self, client, manager_with_token, employee):
        _, headers = manager_with_token
        resp = await client.get(
            "/manager/employee-hours",
            params={"month": 2, "year": 2026},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should list the employee with 0 hours
        emp_data = next((d for d in data if d["user_id"] == str(employee.id)), None)
        assert emp_data is not None
        assert emp_data["total_hours"] == 0.0
        assert emp_data["shift_count"] == 0

    @pytest.mark.anyio
    async def test_calculates_hours_from_schedules(
        self, client, session, manager_with_token, employee, test_shift, test_role
    ):
        _, headers = manager_with_token
        # Add 3 schedules (each 8h shift) in February
        for day in [5, 10, 15]:
            session.add(Schedule(
                date=date(2026, 2, day),
                shift_def_id=test_shift.id,
                user_id=employee.id,
                role_id=test_role.id,
                is_published=False,
            ))
        session.commit()

        resp = await client.get(
            "/manager/employee-hours",
            params={"month": 2, "year": 2026},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        emp_data = next(d for d in data if d["user_id"] == str(employee.id))
        assert emp_data["total_hours"] == 24.0  # 3 shifts × 8h
        assert emp_data["shift_count"] == 3

    @pytest.mark.anyio
    async def test_has_availability_flag(
        self, client, session, manager_with_token, employee, employee2, test_shift
    ):
        _, headers = manager_with_token
        # Employee1 submits availability, Employee2 does not
        session.add(Availability(
            user_id=employee.id,
            date=date(2026, 7, 10),
            shift_def_id=test_shift.id,
            status=AvailabilityStatus.AVAILABLE,
        ))
        session.commit()

        resp = await client.get(
            "/manager/employee-hours",
            params={"month": 7, "year": 2026},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        emp1 = next(d for d in data if d["user_id"] == str(employee.id))
        emp2 = next(d for d in data if d["user_id"] == str(employee2.id))
        assert emp1["has_availability"] is True
        assert emp2["has_availability"] is False

    @pytest.mark.anyio
    async def test_invalid_month_returns_422(self, client, manager_with_token):
        _, headers = manager_with_token
        resp = await client.get(
            "/manager/employee-hours",
            params={"month": 13, "year": 2026},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_overnight_shift_hours(
        self, client, session, manager_with_token, employee, test_role
    ):
        _, headers = manager_with_token
        # Create overnight shift (22:00-06:00 = 8h)
        night_shift = ShiftDefinition(
            name="Night", start_time=time(22, 0), end_time=time(6, 0)
        )
        session.add(night_shift)
        session.commit()
        session.refresh(night_shift)

        session.add(Schedule(
            date=date(2026, 8, 1),
            shift_def_id=night_shift.id,
            user_id=employee.id,
            role_id=test_role.id,
            is_published=False,
        ))
        session.commit()

        resp = await client.get(
            "/manager/employee-hours",
            params={"month": 8, "year": 2026},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        emp_data = next(d for d in data if d["user_id"] == str(employee.id))
        assert emp_data["total_hours"] == 8.0  # 22:00 -> 06:00 = 8h

    @pytest.mark.anyio
    async def test_multiple_employees_sorted(
        self, client, session, manager_with_token, employee, employee2, test_shift, test_role
    ):
        _, headers = manager_with_token
        # Employee1: 2 shifts (16h), Employee2: 3 shifts (24h)
        for day in [1, 2]:
            session.add(Schedule(
                date=date(2026, 9, day),
                shift_def_id=test_shift.id,
                user_id=employee.id,
                role_id=test_role.id,
            ))
        for day in [1, 2, 3]:
            session.add(Schedule(
                date=date(2026, 9, day),
                shift_def_id=test_shift.id,
                user_id=employee2.id,
                role_id=test_role.id,
            ))
        session.commit()

        resp = await client.get(
            "/manager/employee-hours",
            params={"month": 9, "year": 2026},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # Employee2 should be first (more hours)
        assert data[0]["user_id"] == str(employee2.id)
        assert data[0]["total_hours"] == 24.0
        emp1 = next(d for d in data if d["user_id"] == str(employee.id))
        assert emp1["total_hours"] == 16.0
