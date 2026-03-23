from httpx import AsyncClient
import pytest
from sqlmodel import Session, select
from app.models import User, RoleSystem, ShiftDefinition, JobRole, Schedule, Attendance, AttendanceStatus, LeaveRequest, LeaveStatus
from datetime import date, timedelta, time, datetime
from app.auth_utils import create_access_token

@pytest.mark.asyncio
async def test_get_users_with_next_shift(client: AsyncClient, session: Session, manager_token_headers):
    # Setup: Create a shift and schedule for an employee
    shift = ShiftDefinition(name="Test Shift", start_time=time(9,0), end_time=time(17,0), applicable_days="0,1,2,3,4,5,6")
    session.add(shift)
    
    role = JobRole(name="Test Role", color_hex="#FFFFFF")
    session.add(role)
    session.commit()
    
    # Create employee
    employee = User(
        username="employee_next_shift", 
        password_hash="hash", 
        full_name="Next Shift Emp", 
        role_system=RoleSystem.EMPLOYEE
    )
    session.add(employee)
    session.commit()
    
    # Schedule for today or tomorrow
    today = date.today()
    schedule = Schedule(
        date=today,
        shift_def_id=shift.id,
        user_id=employee.id,
        role_id=role.id,
        is_published=True
    )
    session.add(schedule)
    session.commit()
    
    response = await client.get("/manager/users", headers=manager_token_headers)
    assert response.status_code == 200
    users = response.json()
    
    target_user = next((u for u in users if u["username"] == "employee_next_shift"), None)
    assert target_user is not None
    assert target_user["next_shift"] is not None
    assert target_user["next_shift"]["shift_name"] == "Test Shift"
    assert target_user["next_shift"]["role_name"] == "Test Role"
    assert target_user["next_shift"]["date"] == today.isoformat()

@pytest.mark.asyncio
async def test_get_user_stats(client: AsyncClient, session: Session, manager_token_headers):
    # Create employee
    employee = User(
        username="employee_stats", 
        password_hash="hash", 
        full_name="Stats Emp", 
        role_system=RoleSystem.EMPLOYEE
    )
    session.add(employee)
    session.commit()
    
    # Create past attendances
    today = date.today()
    # 2 shifts confirmed
    for i in range(2):
        att = Attendance(
            user_id=employee.id,
            date=today - timedelta(days=i+1),
            check_in=time(9,0),
            check_out=time(17,0),
            status=AttendanceStatus.CONFIRMED
        )
        session.add(att)
    session.commit()
    
    response = await client.get(f"/manager/users/{employee.id}/stats", headers=manager_token_headers)
    assert response.status_code == 200
    data = response.json()
    
    assert data["total_shifts_completed"] == 2
    assert data["total_hours_worked"] == 16.0
    assert len(data["monthly_shifts"]) == 6
    # Current month stats should include these 2 shifts (if they are in current month)
    # If today is 1st of month, previous days might be previous month.
    # But count should assume valid range.

@pytest.mark.asyncio
async def test_dashboard_home(client: AsyncClient, session: Session, manager_token_headers):
    # Setup
    shift = ShiftDefinition(name="Dash Shift", start_time=time(10,0), end_time=time(18,0), applicable_days="0,1,2,3,4,5,6")
    session.add(shift)
    role = JobRole(name="Dash Role", color_hex="#000000")
    session.add(role)
    session.commit()
    
    emp1 = User(username="emp_working", password_hash="h", full_name="Working Emp", role_system=RoleSystem.EMPLOYEE)
    emp2 = User(username="emp_missing", password_hash="h", full_name="Missing Emp", role_system=RoleSystem.EMPLOYEE)
    session.add(emp1)
    session.add(emp2)
    session.commit()
    
    today = date.today()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)
    
    # Emp1 working today
    s1 = Schedule(date=today, shift_def_id=shift.id, user_id=emp1.id, role_id=role.id, is_published=True)
    session.add(s1)
    
    # Emp2 scheduled yesterday but Pending attendance (simulating "missing confirmation")
    s2 = Schedule(date=yesterday, shift_def_id=shift.id, user_id=emp2.id, role_id=role.id, is_published=True)
    session.add(s2)
    
    att_pending = Attendance(
        user_id=emp2.id,
        date=yesterday,
        check_in=time(10,0),
        check_out=time(18,0),
        status=AttendanceStatus.PENDING # Auto-created or manually created but not confirmed
    )
    session.add(att_pending)

    # Add older pending attendance to verify it is fetched
    att_older_pending = Attendance(
        user_id=emp1.id,
        date=two_days_ago,
        check_in=time(10,0),
        check_out=time(18,0),
        status=AttendanceStatus.PENDING
    )
    session.add(att_older_pending)

    # Add a pending leave request
    leave_req = LeaveRequest(
        user_id=emp2.id,
        start_date=today + timedelta(days=1),
        end_date=today + timedelta(days=2),
        reason="Sick",
        status=LeaveStatus.PENDING
    )
    session.add(leave_req)
    
    session.commit()
    
    response = await client.get("/manager/dashboard/home", headers=manager_token_headers)
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["working_today"]) == 1
    assert data["working_today"][0]["user_name"] == "Working Emp"
    
    # Verify both yesterday and two_days_ago are returned
    assert len(data["missing_confirmations"]) == 2
    users_with_missing = {a["user_name"] for a in data["missing_confirmations"]}
    assert "Missing Emp" in users_with_missing
    assert "Working Emp" in users_with_missing

    # Verify pending leave requests
    assert "pending_leave_requests" in data
    assert len(data["pending_leave_requests"]) == 1
    assert data["pending_leave_requests"][0]["user_name"] == "Missing Emp"
    assert data["pending_leave_requests"][0]["reason"] == "Sick"

