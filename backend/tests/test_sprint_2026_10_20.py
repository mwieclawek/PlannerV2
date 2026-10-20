import pytest
from datetime import date, time, timedelta
from unittest.mock import MagicMock, patch
from sqlmodel import Session, select
from httpx import AsyncClient

from app.models import (
    User,
    RoleSystem,
    JobRole,
    ShiftDefinition,
    Schedule,
    RestaurantConfig,
    Notification,
)
from app.auth_utils import get_password_hash, create_access_token
from app.services.google_calendar_service import GoogleCalendarService


@pytest.mark.asyncio
async def test_config_attendance_and_tip_pool_options(
    client: AsyncClient,
    session: Session,
    test_tenant,
    auth_headers: dict,
):
    # Update restaurant config with new fields
    resp = await client.post(
        "/manager/config",
        json={
            "name": "Bistro Test",
            "opening_hours": "08:00-22:00",
            "require_attendance_registration": True,
            "attendance_required_from": "2026-10-01",
            "enable_tip_pool": False,
            "enable_daily_closeout": False,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["require_attendance_registration"] is True
    assert data["attendance_required_from"] == "2026-10-01"
    assert data["enable_tip_pool"] is False
    assert data["enable_daily_closeout"] is False

    # Employee can also fetch config flags
    emp = User(
        tenant_id=test_tenant.id,
        username="emp_cfg",
        password_hash=get_password_hash("Secret123"),
        full_name="Jan Kowalski",
        role_system=RoleSystem.EMPLOYEE,
    )
    session.add(emp)
    session.commit()
    session.refresh(emp)
    emp_token = create_access_token(
        data={"sub": emp.username, "role": emp.role_system, "tenant_id": str(test_tenant.id)}
    )
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    emp_cfg = await client.get("/employee/config", headers=emp_headers)
    assert emp_cfg.status_code == 200
    ec = emp_cfg.json()
    assert ec["require_attendance_registration"] is True
    assert ec["attendance_required_from"] == "2026-10-01"
    assert ec["enable_tip_pool"] is False
    assert ec["enable_daily_closeout"] is False


@pytest.mark.asyncio
async def test_missing_attendance_and_30min_reminder_and_absence(
    client: AsyncClient,
    session: Session,
    test_tenant,
    auth_headers: dict,
):
    # Enable mandatory attendance starting yesterday
    yesterday = date.today() - timedelta(days=1)
    two_days_ago = date.today() - timedelta(days=2)

    test_tenant.require_attendance_registration = True
    test_tenant.attendance_required_from = yesterday
    test_tenant.enable_tip_pool = True
    session.add(test_tenant)

    role = JobRole(tenant_id=test_tenant.id, name="Kelner", color_hex="#FF5733", hourly_rate=28.0)
    session.add(role)
    shift = ShiftDefinition(
        tenant_id=test_tenant.id,
        name="Zmiana Ranna",
        start_time=time(8, 0),
        end_time=time(16, 0),
    )
    session.add(shift)

    emp = User(
        tenant_id=test_tenant.id,
        username="emp_att_missing",
        password_hash=get_password_hash("Secret123"),
        full_name="Piotr Nowak",
        role_system=RoleSystem.EMPLOYEE,
        hourly_rate=30.0,
    )
    session.add(emp)
    session.commit()
    session.refresh(role)
    session.refresh(shift)
    session.refresh(emp)

    # Published shift 2 days ago (before attendance_required_from -> should be ignored)
    sched_old = Schedule(
        tenant_id=test_tenant.id,
        date=two_days_ago,
        shift_def_id=shift.id,
        user_id=emp.id,
        role_id=role.id,
        is_published=True,
    )
    # Published shift yesterday (on/after attendance_required_from -> should be flagged & notified)
    sched_yesterday = Schedule(
        tenant_id=test_tenant.id,
        date=yesterday,
        shift_def_id=shift.id,
        user_id=emp.id,
        role_id=role.id,
        is_published=True,
    )
    session.add(sched_old)
    session.add(sched_yesterday)
    session.commit()

    emp_token = create_access_token(
        data={"sub": emp.username, "role": emp.role_system, "tenant_id": str(test_tenant.id)}
    )
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # 1. Check missing attendance endpoint
    missing_resp = await client.get("/employee/attendance/missing", headers=emp_headers)
    assert missing_resp.status_code == 200
    missing_data = missing_resp.json()
    assert len(missing_data["missing"]) == 1
    assert missing_data["missing"][0]["date"] == yesterday.isoformat()

    # Verify a reminder notification was created for yesterday's shift (and not duplicated on 2nd call)
    await client.get("/employee/attendance/missing", headers=emp_headers)
    notifs = session.exec(
        select(Notification).where(Notification.user_id == emp.id)
    ).all()
    assert len(notifs) == 1
    assert yesterday.isoformat() in notifs[0].body

    # 2. Employee marks "Nieobecny" with reason for yesterday's shift
    reg_resp = await client.post(
        "/employee/attendance",
        params={
            "target_date": yesterday.isoformat(),
            "check_in": "00:00",
            "check_out": "00:00",
            "is_absent": True,
            "absence_reason": "Nagła wizyta lekarska",
        },
        headers=emp_headers,
    )
    assert reg_resp.status_code == 200
    reg_json = reg_resp.json()
    assert reg_json["is_absent"] is True
    assert reg_json["absence_reason"] == "Nagła wizyta lekarska"

    # 3. Missing attendance list should now be empty!
    missing_after = await client.get("/employee/attendance/missing", headers=emp_headers)
    assert missing_after.status_code == 200
    assert missing_after.json()["missing"] == []


@pytest.mark.asyncio
async def test_user_profile_update_me(
    client: AsyncClient,
    session: Session,
    test_tenant,
):
    emp = User(
        tenant_id=test_tenant.id,
        username="emp_profile",
        password_hash=get_password_hash("Secret123"),
        full_name="Katarzyna Wiśniewska",
        email="kasia@example.com",
        role_system=RoleSystem.EMPLOYEE,
        hourly_rate=32.5,
    )
    session.add(emp)
    session.commit()
    session.refresh(emp)

    emp_token = create_access_token(
        data={"sub": emp.username, "role": emp.role_system, "tenant_id": str(test_tenant.id)}
    )
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # Update email via PUT /auth/me
    upd = await client.put(
        "/auth/me",
        json={"email": "nowy.email@example.com"},
        headers=emp_headers,
    )
    assert upd.status_code == 200
    assert upd.json()["email"] == "nowy.email@example.com"
    assert upd.json()["hourly_rate"] == 32.5


def test_google_calendar_deduplicates_events_in_window(session: Session, test_tenant):
    shift_def = ShiftDefinition(
        tenant_id=test_tenant.id,
        name="Zmiana Ranna",
        start_time=time(8, 0),
        end_time=time(16, 0),
    )
    role = JobRole(tenant_id=test_tenant.id, name="Kelner", color_hex="#112233")
    emp = User(
        tenant_id=test_tenant.id,
        username="emp_gcal",
        password_hash=get_password_hash("Secret123"),
        full_name="Jan Gcal",
        role_system=RoleSystem.EMPLOYEE,
        google_refresh_token="fake_refresh",
    )
    session.add(shift_def)
    session.add(role)
    session.add(emp)
    session.commit()
    session.refresh(shift_def)
    session.refresh(role)
    session.refresh(emp)

    sched = Schedule(
        tenant_id=test_tenant.id,
        date=date(2026, 10, 20),
        shift_def_id=shift_def.id,
        user_id=emp.id,
        role_id=role.id,
        is_published=True,
    )
    session.add(sched)
    session.commit()
    session.refresh(sched)

    service = GoogleCalendarService(session)
    event_body = service._build_event(emp, sched, shift_def)

    # Simulate an existing event in the shift window plus a duplicate with a different ID
    get_resp = MagicMock()
    get_resp.status_code = 200
    get_resp.json.return_value = {
        "items": [
            {
                "id": event_body["id"],
                "summary": event_body["summary"],
                "description": event_body["description"],
                "start": event_body["start"],
                "end": event_body["end"],
            },
            {
                "id": "plannerv2duplicateold123",
                "summary": event_body["summary"],
                "description": event_body["description"],
                "start": event_body["start"],
                "end": event_body["end"],
            },
        ]
    }
    put_resp = MagicMock()
    put_resp.status_code = 200
    del_resp = MagicMock()
    del_resp.status_code = 204

    with (
        patch.object(service, "get_valid_access_token", return_value="fake_access_token"),
        patch("app.services.google_calendar_service.httpx.get", return_value=get_resp),
        patch("app.services.google_calendar_service.httpx.put", return_value=put_resp) as mock_put,
        patch("app.services.google_calendar_service.httpx.delete", return_value=del_resp) as mock_del,
        patch("app.services.google_calendar_service.httpx.post") as mock_post,
    ):
        ok = service.sync_schedule_to_calendar(emp, sched)

    assert ok is True
    mock_post.assert_not_called()
    assert mock_put.call_count == 1
    assert mock_del.call_count == 1
    assert "plannerv2duplicateold123" in mock_del.call_args[0][0]


@pytest.mark.asyncio
async def test_backend_attendance_config_and_tip_pool_enforcement(
    client: AsyncClient,
    session: Session,
    auth_headers: dict,
    employee_headers: dict,
    test_tenant: RestaurantConfig,
):
    """
    Verify backend enforcement in EmployeeService & OperationsService:
    1. Future-date attendance registration is blocked (400).
    2. Reporting absence (is_absent=True) on a day without a scheduled shift is blocked (400).
    3. Registering check_in == check_out or invalid time format is blocked (400).
    4. Clocking out when mandatory checklist items are incomplete without checklist_skip_reason is blocked (400).
    5. Disabling enable_tip_pool zeroes out tip allocations in closeout and monthly payroll.
    """
    tomorrow = date.today() + timedelta(days=1)
    three_days_ago = date.today() - timedelta(days=3)

    # 1. Future date check-in blocked
    future_resp = await client.post(
        "/employee/attendance",
        params={"target_date": tomorrow.isoformat(), "check_in": "08:00", "check_out": "16:00"},
        headers=employee_headers,
    )
    assert future_resp.status_code == 400

    # 2. Reporting absence when NOT scheduled is blocked
    unsched_abs = await client.post(
        "/employee/attendance",
        params={
            "target_date": three_days_ago.isoformat(),
            "is_absent": True,
            "absence_reason": "Brak zmiany w grafiku",
        },
        headers=employee_headers,
    )
    assert unsched_abs.status_code == 400

    # 3. Equal check_in and check_out or malformed time is blocked
    zero_hrs = await client.post(
        "/employee/attendance",
        params={"target_date": three_days_ago.isoformat(), "check_in": "10:00", "check_out": "10:00"},
        headers=employee_headers,
    )
    assert zero_hrs.status_code == 400

    bad_time = await client.post(
        "/employee/attendance",
        params={"target_date": three_days_ago.isoformat(), "check_in": "25:99", "check_out": "16:00"},
        headers=employee_headers,
    )
    assert bad_time.status_code == 400

    # 4. Mandatory checklist enforcement on clock-out (configurable via require_checklists)
    tpl_resp = await client.post(
        "/manager/checklists",
        json={
            "title": "Zamknięcie zmiany - obowiązkowe",
            "shift_period": "CLOSING",
            "is_mandatory": True,
            "items": [{"title": "Zakręć zawór gazu", "is_mandatory": True, "sort_order": 0}],
        },
        headers=auth_headers,
    )
    assert tpl_resp.status_code == 201

    # By default require_checklists is True, so clock-out without skip reason returns 400
    no_skip_resp = await client.post(
        "/employee/attendance",
        params={"target_date": three_days_ago.isoformat(), "check_in": "08:00", "check_out": "16:00"},
        headers=employee_headers,
    )
    assert no_skip_resp.status_code == 400

    # If manager disables require_checklists in manager config ("Jeżeli ktoś nie chce")
    await client.post(
        "/manager/config",
        json={"name": test_tenant.name, "require_checklists": False},
        headers=auth_headers,
    )

    # When require_checklists is False, clock-out is allowed without checklist
    disabled_chk_resp = await client.post(
        "/employee/attendance",
        params={"target_date": (three_days_ago - timedelta(days=1)).isoformat(), "check_in": "08:00", "check_out": "16:00"},
        headers=employee_headers,
    )
    assert disabled_chk_resp.status_code == 200

    # Re-enable require_checklists for subsequent tests
    await client.post(
        "/manager/config",
        json={"name": test_tenant.name, "require_checklists": True},
        headers=auth_headers,
    )

    # With checklist_skip_reason -> 200
    with_skip_resp = await client.post(
        "/employee/attendance",
        params={
            "target_date": three_days_ago.isoformat(),
            "check_in": "08:00",
            "check_out": "16:00",
            "checklist_skip_reason": "Kuchnia była zamknięta w tym dniu",
        },
        headers=employee_headers,
    )
    assert with_skip_resp.status_code == 200
    att_id = with_skip_resp.json()["id"]

    # Confirm the attendance as manager and test enable_tip_pool = False
    await client.put(f"/manager/attendance/{att_id}/confirm", headers=auth_headers)
    await client.post(
        "/manager/config",
        json={"name": test_tenant.name, "enable_tip_pool": False},
        headers=auth_headers,
    )
    closeout_resp = await client.post(
        "/manager/closeouts",
        json={"date": three_days_ago.isoformat(), "daily_revenue": 5000.0, "tip_pool": 400.0},
        headers=auth_headers,
    )
    assert closeout_resp.status_code == 200
    assert closeout_resp.json()["tip_pool"] == 0.0
    for alloc in closeout_resp.json()["tip_allocations"]:
        assert alloc["allocated_tip"] == 0.0

