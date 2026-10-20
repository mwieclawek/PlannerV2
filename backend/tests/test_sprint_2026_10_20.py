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
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["require_attendance_registration"] is True
    assert data["attendance_required_from"] == "2026-10-01"
    assert data["enable_tip_pool"] is False

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
