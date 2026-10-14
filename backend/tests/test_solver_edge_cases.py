import uuid
from datetime import date, time, timedelta

import pytest
from sqlmodel import Session

from app.auth_utils import get_password_hash
from app.models import (
    Availability, AvailabilityStatus, JobRole, RoleSystem, ShiftDefinition, User,
)


@pytest.fixture
def impossible_scenario(session: Session, test_tenant):
    """1 employee with a rare role who is available; the requirement demands 10 people."""
    role = JobRole(tenant_id=test_tenant.id, name=f"RareRole_{uuid.uuid4().hex[:4]}", color_hex="#FF0000")
    shift = ShiftDefinition(tenant_id=test_tenant.id, name="HardShift", start_time=time(8, 0), end_time=time(16, 0))
    session.add_all([role, shift])
    session.commit()
    session.refresh(role)
    session.refresh(shift)

    emp = User(
        tenant_id=test_tenant.id,
        username=f"employee_{uuid.uuid4().hex[:8]}",
        password_hash=get_password_hash("Testpass123"),
        full_name="Test Employee",
        role_system=RoleSystem.EMPLOYEE,
    )
    emp.job_roles = [role]
    session.add(emp)
    session.commit()
    session.refresh(emp)

    test_date = date.today() + timedelta(days=2)
    session.add(Availability(
        user_id=emp.id, date=test_date, shift_def_id=shift.id, status=AvailabilityStatus.AVAILABLE,
    ))
    session.commit()
    return {"role_id": role.id, "shift_id": shift.id, "test_date": test_date}


class TestSolverEdgeCases:
    @pytest.mark.asyncio
    async def test_solver_impossible_constraints(self, client, auth_headers, impossible_scenario):
        data = impossible_scenario

        # We have 1 employee. We demand 10.
        resp = await client.post("/manager/requirements", headers=auth_headers, json=[{
            "date": str(data["test_date"]),
            "shift_def_id": data["shift_id"],
            "role_id": data["role_id"],
            "min_count": 10,
        }])
        assert resp.status_code == 200

        res = await client.post("/scheduler/generate", headers=auth_headers, json={
            "start_date": str(data["test_date"]),
            "end_date": str(data["test_date"]),
        })
        assert res.status_code == 200
        result_json = res.json()

        # The solver must not claim a clean success when the demand cannot be met
        assert result_json.get("status") != "success" or "warnings" in result_json
