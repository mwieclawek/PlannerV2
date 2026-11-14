from datetime import date, time
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlmodel import Session

from app.auth_utils import get_password_hash
from app.models import (
    Attendance,
    AttendanceStatus,
    JobRole,
    RoleSystem,
    Schedule,
    ShiftDefinition,
    User,
    UserJobRoleLink,
)


@pytest.mark.asyncio
async def test_monthly_hours_worked_and_planned(
    client: AsyncClient,
    session: Session,
    auth_headers: dict,
    test_tenant,
):
    """Verify /manager/employee-hours and /manager/users/{id}/stats?month=&year= return worked & planned hours."""
    role = JobRole(tenant_id=test_tenant.id, name="KelnerTest", color_hex="#123456")
    shift = ShiftDefinition(
        tenant_id=test_tenant.id,
        name="Zmiana 8h",
        start_time=time(10, 0),
        end_time=time(18, 0),
    )
    emp = User(
        tenant_id=test_tenant.id,
        username=f"hours_emp_{uuid4().hex[:6]}",
        password_hash=get_password_hash("Pass1234"),
        full_name="Anna Godzinowa",
        role_system=RoleSystem.EMPLOYEE,
        target_hours_per_month=160,
    )
    session.add_all([role, shift, emp])
    session.commit()
    session.refresh(role)
    session.refresh(shift)
    session.refresh(emp)

    session.add(UserJobRoleLink(user_id=emp.id, role_id=role.id))

    # Month 2026-10: 2 scheduled shifts (16h planned) and 1 confirmed attendance of 9h worked
    session.add(
        Schedule(
            date=date(2026, 10, 5),
            shift_def_id=shift.id,
            user_id=emp.id,
            role_id=role.id,
            is_published=True,
        )
    )
    session.add(
        Schedule(
            date=date(2026, 10, 6),
            shift_def_id=shift.id,
            user_id=emp.id,
            role_id=role.id,
            is_published=True,
        )
    )
    session.add(
        Attendance(
            user_id=emp.id,
            date=date(2026, 10, 5),
            check_in=time(10, 0),
            check_out=time(19, 0),
            status=AttendanceStatus.CONFIRMED,
            is_absent=False,
        )
    )
    # Different month 2026-09: should not leak into 2026-10
    session.add(
        Attendance(
            user_id=emp.id,
            date=date(2026, 9, 20),
            check_in=time(10, 0),
            check_out=time(15, 0),
            status=AttendanceStatus.CONFIRMED,
            is_absent=False,
        )
    )
    session.commit()

    # 1. Check /manager/employee-hours for 2026-10
    r_list = await client.get(
        "/manager/employee-hours",
        params={"month": 10, "year": 2026},
        headers=auth_headers,
    )
    assert r_list.status_code == 200
    rows = r_list.json()
    emp_row = next((r for r in rows if r["user_id"] == str(emp.id)), None)
    assert emp_row is not None
    assert emp_row["planned_hours"] == 16.0
    assert emp_row["total_hours"] == 16.0
    assert emp_row["worked_hours"] == 9.0
    assert emp_row["shift_count"] == 2
    assert emp_row["worked_shift_count"] == 1
    assert emp_row["target_hours_per_month"] == 160

    # 2. Check /manager/users/{id}/stats for 2026-10 and 2026-09
    r_oct = await client.get(
        f"/manager/users/{emp.id}/stats",
        params={"month": 10, "year": 2026},
        headers=auth_headers,
    )
    assert r_oct.status_code == 200
    oct_data = r_oct.json()
    assert oct_data["selected_month"] == "2026-10"
    assert oct_data["selected_month_worked_hours"] == 9.0
    assert oct_data["selected_month_planned_hours"] == 16.0
    assert oct_data["selected_month_shifts"] == 1
    assert oct_data["target_hours_per_month"] == 160

    r_sep = await client.get(
        f"/manager/users/{emp.id}/stats",
        params={"month": 9, "year": 2026},
        headers=auth_headers,
    )
    assert r_sep.status_code == 200
    sep_data = r_sep.json()
    assert sep_data["selected_month"] == "2026-09"
    assert sep_data["selected_month_worked_hours"] == 5.0
    assert sep_data["selected_month_planned_hours"] == 0.0
    assert sep_data["selected_month_shifts"] == 1
