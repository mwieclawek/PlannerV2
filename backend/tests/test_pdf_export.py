import pytest
from datetime import date, time
from uuid import uuid4
from backend.app.models import User, RoleSystem, Attendance, AttendanceStatus
from backend.app.auth_utils import get_password_hash, create_access_token

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

class TestExportAttendancePdf:
    """Tests for GET /manager/attendance/export"""

    @pytest.mark.anyio
    async def test_export_pdf_returns_200(self, client, session, manager_with_token, employee):
        _, headers = manager_with_token
        token = headers["Authorization"].split(" ")[1]

        # Create attendance data
        session.add(Attendance(
            user_id=employee.id,
            date=date(2026, 2, 10),
            check_in=time(8, 0),
            check_out=time(16, 0),
            was_scheduled=True,
            status=AttendanceStatus.CONFIRMED,
        ))
        session.commit()

        resp = await client.get(
            "/manager/attendance/export",
            params={
                "start_date": "2026-02-01",
                "end_date": "2026-02-28",
                "token": token
            }
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}. Content: {resp.text}"
        assert resp.headers["content-type"] == "application/pdf"
        assert len(resp.content) > 100
