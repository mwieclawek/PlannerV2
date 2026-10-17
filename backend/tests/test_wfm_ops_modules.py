import pytest
from datetime import date, time
from uuid import uuid4
from unittest.mock import patch, MagicMock
from sqlmodel import Session, select
from httpx import AsyncClient

from app.models import (
    User,
    RoleSystem,
    JobRole,
    ShiftDefinition,
    Schedule,
    Attendance,
    AttendanceStatus,
    UserDevice,
    RestaurantConfig,
    Notification,
)
from app.auth_utils import get_password_hash, create_access_token
from app.services.push_service import send_push_to_tokens


# ==============================================================================
# PART 1: PushService Data String Casting & Stale Token Removal Tests
# ==============================================================================

def test_push_service_casts_data_and_removes_unregistered_tokens(session: Session, test_tenant):
    user = User(
        tenant_id=test_tenant.id,
        username="push_user",
        password_hash=get_password_hash("secret"),
        full_name="Push User",
        role_system=RoleSystem.EMPLOYEE,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    dev_valid = UserDevice(user_id=user.id, fcm_token="valid_fcm_token_123", device_name="Chrome Web")
    dev_stale = UserDevice(user_id=user.id, fcm_token="stale_fcm_token_456", device_name="Safari iOS")
    session.add(dev_valid)
    session.add(dev_stale)
    session.commit()

    class FakeUnregisteredError(Exception):
        code = "UNREGISTERED"

    resp_ok = MagicMock()
    resp_ok.success = True
    resp_ok.exception = None

    resp_stale = MagicMock()
    resp_stale.success = False
    resp_stale.exception = FakeUnregisteredError("Token is unregistered")

    fake_batch_response = MagicMock()
    fake_batch_response.failure_count = 1
    fake_batch_response.responses = [resp_ok, resp_stale]

    captured_messages = []

    def fake_send_each_for_multicast(msg):
        captured_messages.append(msg)
        return fake_batch_response

    with patch("app.services.push_service.firebase_initialized", True), \
         patch("app.services.push_service.messaging.send_each_for_multicast", side_effect=fake_send_each_for_multicast):

        raw_uuid = uuid4()
        send_push_to_tokens(
            tokens=["valid_fcm_token_123", "stale_fcm_token_456"],
            title="Test Title",
            body="Test Body",
            data={"announcement_id": raw_uuid, "count": 42, 100: True},
            session=session,
        )

        assert len(captured_messages) == 1
        sent_msg = captured_messages[0]
        # Verify all keys and values in data were cast to str
        assert sent_msg.data["announcement_id"] == str(raw_uuid)
        assert sent_msg.data["count"] == "42"
        assert sent_msg.data["100"] == "True"

        # Verify stale token was deleted from UserDevice while valid token remains
        remaining = session.exec(select(UserDevice).where(UserDevice.user_id == user.id)).all()
        assert [d.fcm_token for d in remaining] == ["valid_fcm_token_123"]


# ==============================================================================
# PART 2 — MODULE A: Payroll, Daily Closeout, Tip Pooling & Labor Cost %
# ==============================================================================

@pytest.mark.asyncio
async def test_module_a_payroll_closeout_and_tip_pooling(
    client: AsyncClient,
    session: Session,
    test_tenant,
    auth_headers: dict,
):
    # 1. Create role with hourly_rate = 30.0 PLN
    role_resp = await client.post(
        "/manager/roles",
        json={"name": "Barman", "color_hex": "#123456", "hourly_rate": 30.0},
        headers=auth_headers,
    )
    assert role_resp.status_code == 200
    role_data = role_resp.json()
    assert role_data["hourly_rate"] == 30.0
    role_id = role_data["id"]

    # 2. Create two employees:
    # Employee 1: personal hourly_rate = 40.0 PLN
    # Employee 2: no personal hourly_rate (inherits 30.0 PLN from Barman role)
    emp1 = User(
        tenant_id=test_tenant.id,
        username="emp_payroll_1",
        password_hash=get_password_hash("secret"),
        full_name="Anna Nowak",
        role_system=RoleSystem.EMPLOYEE,
        hourly_rate=40.0,
    )
    emp2 = User(
        tenant_id=test_tenant.id,
        username="emp_payroll_2",
        password_hash=get_password_hash("secret"),
        full_name="Piotr Kowalski",
        role_system=RoleSystem.EMPLOYEE,
        hourly_rate=None,
    )
    session.add(emp1)
    session.add(emp2)
    session.commit()
    session.refresh(emp1)
    session.refresh(emp2)

    # Assign Barman role to emp2
    await client.put(
        f"/manager/users/{emp2.id}/roles",
        json={"role_ids": [role_id]},
        headers=auth_headers,
    )

    # 3. Create shift definition and confirmed attendances on 2026-10-15
    target_day = date(2026, 10, 15)
    shift_def = ShiftDefinition(
        tenant_id=test_tenant.id,
        name="Zmiana Dzien",
        start_time=time(10, 0),
        end_time=time(18, 0),
    )
    session.add(shift_def)
    session.commit()
    session.refresh(shift_def)

    # Emp 1 worked 6 hours CONFIRMED (10:00 - 16:00) -> 6 * 40 = 240 PLN
    # Emp 2 worked 2 hours CONFIRMED (16:00 - 18:00) -> 2 * 30 = 60 PLN
    # Total confirmed hours on 2026-10-15 = 8.0h; Total labor cost = 300 PLN
    att1 = Attendance(
        user_id=emp1.id,
        date=target_day,
        check_in=time(10, 0),
        check_out=time(16, 0),
        was_scheduled=True,
        status=AttendanceStatus.CONFIRMED,
    )
    att2 = Attendance(
        user_id=emp2.id,
        date=target_day,
        check_in=time(16, 0),
        check_out=time(18, 0),
        was_scheduled=True,
        status=AttendanceStatus.CONFIRMED,
    )
    # Also add a PENDING attendance for Emp 2 on 2026-10-16 (4 hours)
    att2_pending = Attendance(
        user_id=emp2.id,
        date=date(2026, 10, 16),
        check_in=time(12, 0),
        check_out=time(16, 0),
        was_scheduled=False,
        status=AttendanceStatus.PENDING,
    )
    session.add_all([att1, att2, att2_pending])
    session.commit()

    # 4. Manager submits Daily Closeout for 2026-10-15:
    # Revenue = 1500 PLN, Tip Pool = 160 PLN
    # Expected Labor Cost % = (300 / 1500) * 100 = 20.0%
    # Expected Tip Pooling:
    #   Emp 1 (6h / 8h = 75% of 160 PLN) = 120.0 PLN
    #   Emp 2 (2h / 8h = 25% of 160 PLN) = 40.0 PLN
    closeout_resp = await client.post(
        "/manager/closeouts",
        json={
            "date": target_day.isoformat(),
            "daily_revenue": 1500.0,
            "tip_pool": 160.0,
            "notes": "Dobry czwartek",
        },
        headers=auth_headers,
    )
    assert closeout_resp.status_code == 200
    c_data = closeout_resp.json()
    assert c_data["daily_revenue"] == 1500.0
    assert c_data["tip_pool"] == 160.0
    assert c_data["confirmed_hours"] == 8.0
    assert c_data["labor_cost"] == 300.0
    assert c_data["labor_cost_pct"] == 20.0
    assert c_data["is_closed_out"] is True

    # Verify dashboard home includes daily_closeout
    dash_resp = await client.get(
        f"/manager/dashboard/home?date={target_day.isoformat()}",
        headers=auth_headers,
    )
    assert dash_resp.status_code == 200
    assert dash_resp.json()["daily_closeout"]["labor_cost_pct"] == 20.0

    # 5. Check Manager Monthly Payroll Summary for 2026-10
    payroll_resp = await client.get(
        "/manager/payroll?year=2026&month=10",
        headers=auth_headers,
    )
    assert payroll_resp.status_code == 200
    p_data = payroll_resp.json()
    assert p_data["total_monthly_revenue"] == 1500.0
    assert p_data["total_tips"] == 160.0
    assert p_data["total_base_pay"] == 300.0
    assert p_data["monthly_labor_cost_pct"] == 20.0

    entries_by_name = {e["user_name"]: e for e in p_data["items"]}
    anna = entries_by_name["Anna Nowak"]
    assert anna["confirmed_hours"] == 6.0
    assert anna["hourly_rate"] == 40.0
    assert anna["base_pay"] == 240.0
    assert anna["allocated_tips"] == 120.0
    assert anna["total_pay"] == 360.0

    piotr = entries_by_name["Piotr Kowalski"]
    assert piotr["confirmed_hours"] == 2.0
    assert piotr["pending_hours"] == 4.0
    assert piotr["hourly_rate"] == 30.0
    assert piotr["base_pay"] == 60.0
    assert piotr["allocated_tips"] == 40.0
    assert piotr["total_pay"] == 100.0

    # 6. Check Employee's own earnings endpoint
    emp1_token = create_access_token(data={"sub": emp1.username, "tenant_id": str(test_tenant.id)})
    my_pay_resp = await client.get(
        "/employee/payroll/my?year=2026&month=10",
        headers={"Authorization": f"Bearer {emp1_token}"},
    )
    assert my_pay_resp.status_code == 200
    my_pay = my_pay_resp.json()
    assert my_pay["base_pay"] == 240.0
    assert my_pay["allocated_tips"] == 120.0
    assert my_pay["total_pay"] == 360.0

    # 7. Check CSV and PDF Exports
    csv_resp = await client.get(
        "/manager/payroll/export/csv?year=2026&month=10",
        headers=auth_headers,
    )
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["content-type"]
    assert "Anna Nowak" in csv_resp.text

    pdf_resp = await client.get(
        "/manager/payroll/export/pdf?year=2026&month=10",
        headers=auth_headers,
    )
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF")


# ==============================================================================
# PART 2 — MODULE B: Operational Checklists & Digital HACCP Cards
# ==============================================================================

@pytest.mark.asyncio
async def test_module_b_checklists_and_clockout_validation(
    client: AsyncClient,
    session: Session,
    test_tenant,
    auth_headers: dict,
    employee_headers: dict,
):
    # 1. Manager creates a CLOSING checklist with one mandatory item and one optional item
    create_resp = await client.post(
        "/manager/checklists",
        json={
            "title": "Zamkniecie zmiany barowej",
            "shift_period": "CLOSING",
            "is_mandatory": True,
            "is_active": True,
            "items": [
                {"title": "Zakręcenie zaworów CO2", "is_mandatory": True, "sort_order": 1},
                {"title": "Wyrzucenie szkła", "is_mandatory": False, "sort_order": 2},
            ],
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    tpl = create_resp.json()
    assert len(tpl["items"]) == 2
    mandatory_item_id = next(i["id"] for i in tpl["items"] if i["is_mandatory"])

    target_day = date(2026, 10, 17)

    # 2. Employee checks clock-out validation BEFORE completing mandatory item
    val_before = await client.get(
        f"/employee/checklists/validate-clockout?target_date={target_day.isoformat()}",
        headers=employee_headers,
    )
    assert val_before.status_code == 200
    vb_data = val_before.json()
    assert vb_data["all_mandatory_completed"] is False
    assert vb_data["missing_mandatory_count"] == 1
    assert any("Zakręcenie zaworów CO2" in m["item_title"] for m in vb_data["missing_items"])

    # 3. Employee completes the mandatory item
    toggle_resp = await client.post(
        f"/employee/checklists/items/{mandatory_item_id}/toggle",
        json={"date": target_day.isoformat(), "is_completed": True},
        headers=employee_headers,
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["is_completed"] is True

    # 4. Employee checks clock-out validation AFTER completing mandatory item
    val_after = await client.get(
        f"/employee/checklists/validate-clockout?target_date={target_day.isoformat()}",
        headers=employee_headers,
    )
    assert val_after.status_code == 200
    assert val_after.json()["all_mandatory_completed"] is True
    assert val_after.json()["missing_items"] == []

    # 5. Employee registers attendance with optional checklist_skip_reason
    att_resp = await client.post(
        f"/employee/attendance?target_date={target_day.isoformat()}&check_in=08:00&check_out=16:00&checklist_skip_reason=Awaria+zaworu",
        headers=employee_headers,
    )
    assert att_resp.status_code == 200
    assert att_resp.json()["checklist_skip_reason"] == "Awaria zaworu"


@pytest.mark.asyncio
async def test_module_b_haccp_registry_and_sanepid_pdf(
    client: AsyncClient,
    auth_headers: dict,
    employee_headers: dict,
):
    # 1. Manager creates a HACCP cooling device (norm: 0.0 to 4.0 C)
    dev_resp = await client.post(
        "/manager/haccp/devices",
        json={
            "name": "Chłodnia Mięsna #1",
            "min_temp": 0.0,
            "max_temp": 4.0,
            "is_active": True,
        },
        headers=auth_headers,
    )
    assert dev_resp.status_code == 201
    device_id = dev_resp.json()["id"]

    today_str = date.today().isoformat()

    # 2. Employee logs a normal temperature (2.5 C -> within norm)
    log_ok = await client.post(
        "/employee/haccp/logs",
        json={
            "log_type": "TEMPERATURE",
            "device_id": device_id,
            "measured_temp": 2.5,
        },
        headers=employee_headers,
    )
    assert log_ok.status_code == 201
    assert log_ok.json()["is_within_norm"] is True
    assert log_ok.json()["user_name"] == "Test Employee"

    # 3. Employee logs an out-of-norm temperature (7.8 C -> violation!)
    log_bad = await client.post(
        "/employee/haccp/logs",
        json={
            "log_type": "TEMPERATURE",
            "device_id": device_id,
            "measured_temp": 7.8,
            "corrective_action": "Wezwano serwis chłodniczy, przeniesiono towar do chłodni #2",
        },
        headers=employee_headers,
    )
    assert log_bad.status_code == 201
    assert log_bad.json()["is_within_norm"] is False
    assert "serwis" in log_bad.json()["corrective_action"]

    # 4. Employee logs a sanitation/cleaning entry
    log_clean = await client.post(
        "/employee/haccp/logs",
        json={
            "log_type": "SANITATION",
            "device_name": "Krajalnica i blaty robocze",
            "corrective_action": "Dezynfekcja środkiem Virkon",
        },
        headers=employee_headers,
    )
    assert log_clean.status_code == 201
    assert log_clean.json()["log_type"] == "SANITATION"

    # 5. Manager exports Sanepid PDF report
    pdf_resp = await client.get(
        f"/manager/haccp/export/pdf?start_date={today_str}&end_date={today_str}",
        headers=auth_headers,
    )
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF")


# ==============================================================================
# PART 2 — MODULE C: Announcement Board with Read Receipts & Multi-Tenancy
# ==============================================================================

@pytest.mark.asyncio
async def test_module_c_announcements_and_read_receipts(
    client: AsyncClient,
    session: Session,
    test_tenant,
    auth_headers: dict,
    employee_headers: dict,
):
    # Guarantee employee exists before publishing announcement
    assert employee_headers is not None

    # 1. Manager publishes an announcement
    ann_resp = await client.post(
        "/manager/announcements",
        json={
            "title": "Nowe menu jesienne od piątku",
            "content": "Prosimy o zapoznanie się z alergenami nowego menu.",
            "is_pinned": True,
        },
        headers=auth_headers,
    )
    assert ann_resp.status_code == 201
    ann = ann_resp.json()
    ann_id = ann["id"]
    assert ann["read_count"] == 0
    assert ann["total_target_count"] >= 1

    # Verify in-app Notification was automatically created for the employee
    emp_user = session.exec(select(User).where(User.username == "employee_test")).first()
    notifs = session.exec(select(Notification).where(Notification.user_id == emp_user.id)).all()
    assert any("Nowe menu jesienne" in n.title for n in notifs)

    # 2. Employee fetches announcements -> sees it as unread (is_read=False)
    emp_list_resp = await client.get("/employee/announcements", headers=employee_headers)
    assert emp_list_resp.status_code == 200
    emp_anns = emp_list_resp.json()
    assert len(emp_anns) == 1
    assert emp_anns[0]["id"] == ann_id
    assert emp_anns[0]["is_read"] is False

    # 3. Employee clicks "Zapoznałem się" (marks announcement as read)
    read_resp = await client.post(
        f"/employee/announcements/{ann_id}/read",
        headers=employee_headers,
    )
    assert read_resp.status_code == 200
    assert read_resp.json()["status"] == "read"

    # 4. Manager checks read receipts summary
    receipts_resp = await client.get(
        f"/manager/announcements/{ann_id}/receipts",
        headers=auth_headers,
    )
    assert receipts_resp.status_code == 200
    r_data = receipts_resp.json()
    assert r_data["read_count"] == 1
    assert any(r["user_name"] == "Test Employee" for r in r_data["read_by"])


@pytest.mark.asyncio
async def test_multi_tenant_isolation_and_rbac_for_new_modules(
    client: AsyncClient,
    session: Session,
    auth_headers: dict,
    employee_headers: dict,
):
    # Employee cannot call manager endpoints
    emp_forbidden = await client.post(
        "/manager/announcements",
        json={"title": "Hack", "content": "Nope"},
        headers=employee_headers,
    )
    assert emp_forbidden.status_code == 403

    # Create a record in Tenant A
    ann_resp = await client.post(
        "/manager/announcements",
        json={"title": "Tenant A Secret", "content": "Confidential"},
        headers=auth_headers,
    )
    assert ann_resp.status_code == 201
    tenant_a_ann_id = ann_resp.json()["id"]

    # Create Tenant B and Manager B
    tenant_b = RestaurantConfig(name="Other Restaurant", slug="other-rest")
    session.add(tenant_b)
    session.commit()
    session.refresh(tenant_b)

    mgr_b = User(
        tenant_id=tenant_b.id,
        username="manager_b",
        password_hash=get_password_hash("secret"),
        full_name="Manager B",
        role_system=RoleSystem.MANAGER,
    )
    session.add(mgr_b)
    session.commit()
    session.refresh(mgr_b)

    mgr_b_token = create_access_token(data={"sub": mgr_b.username, "tenant_id": str(tenant_b.id)})
    mgr_b_headers = {"Authorization": f"Bearer {mgr_b_token}"}

    # Manager B sees 0 announcements
    b_list = await client.get("/manager/announcements", headers=mgr_b_headers)
    assert b_list.status_code == 200
    assert b_list.json() == []

    # Manager B cannot view receipts or delete Tenant A's announcement
    b_receipts = await client.get(f"/manager/announcements/{tenant_a_ann_id}/receipts", headers=mgr_b_headers)
    assert b_receipts.status_code == 404


def test_push_service_in_memory_json_credentials(monkeypatch):
    """Verify _ensure_firebase_initialized supports FIREBASE_CREDENTIALS_JSON in memory."""
    from unittest.mock import MagicMock
    from app.services import push_service

    monkeypatch.setattr(push_service, "firebase_initialized", False)
    monkeypatch.setattr(push_service.firebase_admin, "_apps", {})
    mock_cert = MagicMock(return_value="mock-cred-obj")
    mock_init = MagicMock()
    monkeypatch.setattr(push_service.credentials, "Certificate", mock_cert)
    monkeypatch.setattr(push_service.firebase_admin, "initialize_app", mock_init)
    monkeypatch.setenv("FIREBASE_CREDENTIALS_JSON", '{"type": "service_account", "project_id": "test-proj"}')

    assert push_service._ensure_firebase_initialized() is True
    mock_cert.assert_called_once_with({"type": "service_account", "project_id": "test-proj"})
    mock_init.assert_called_once_with("mock-cred-obj")
    monkeypatch.setattr(push_service, "firebase_initialized", False)

