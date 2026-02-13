import pytest
from datetime import date
from sqlmodel import Session, select
from backend.app.models import User, ShiftDefinition, JobRole, StaffingRequirement, RoleSystem, UserJobRoleLink
from backend.app.services.solver import SolverService

@pytest.mark.asyncio
async def test_no_disposition_means_unavailable(session: Session):
    # 1. Setup Data
    # Create Role
    role = JobRole(name="Waiter", color_hex="#000000")
    session.add(role)
    session.commit()
    session.refresh(role)

    # Create User (Employee) linked to Role
    user = User(
        username="lazy_employee", 
        password_hash="hash", 
        full_name="Lazy Employee", 
        role_system=RoleSystem.EMPLOYEE
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    link = UserJobRoleLink(user_id=user.id, role_id=role.id)
    session.add(link)
    session.commit()

    # Create Shift (09:00 - 17:00)
    from datetime import time as time_type
    
    shift = ShiftDefinition(
        name="Day Shift", 
        start_time=time_type(9, 0), 
        end_time=time_type(17, 0),
        applicable_days="0,1,2,3,4,5,6"
    )
    session.add(shift)
    session.commit()
    session.refresh(shift)

    # Create Requirement: Need 1 Waiter for today
    today = date.today()
    req = StaffingRequirement(
        shift_def_id=shift.id,
        role_id=role.id,
        min_count=1,
        date=today
    )
    session.add(req)
    session.commit()

    # DO NOT create Availability (User has no disposition)

    # 2. Run Solver
    solver = SolverService(session)
    result = solver.solve(today, today, save=False)

    # 3. Assertions
    # The user should NOT be assigned because they didn't say they are available.
    # Currently (Bug), they default to AVAILABLE and will be assigned to meet requirement.
    
    assigned_users = [s.user_id for s in result["schedules"]]
    
    # Expected behavior: User should NOT be in assigned_users
    assert user.id not in assigned_users, "User without disposition was assigned a shift! (Defect: No disposition treated as Available)"
