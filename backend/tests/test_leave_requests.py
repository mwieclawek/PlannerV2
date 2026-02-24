"""
Tests for Leave Request feature (Feature 1 from backend_instructions.md).

Covers:
- Employee creates a request → 201
- Employee lists own requests
- Employee cancels a PENDING request
- Manager approves → status changes + availability records created  (CRITICAL)
- Manager rejects → status changes, no availability records
- Overlap validation → 400
- Past date validation → 400
"""
import pytest
import pytest_asyncio
from datetime import date, timedelta
from httpx import AsyncClient
from sqlmodel import Session


# ── date helpers ───────────────────────────────────────────────────────────────

def _in_days(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()

def _yesterday() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


# ── extra employee fixture (for multi-user tests) ──────────────────────────────

@pytest_asyncio.fixture(name="employee2_headers")
async def employee2_headers_fixture(session: Session) -> dict:
    from app.models import User, RoleSystem
    from app.auth_utils import get_password_hash, create_access_token

    user = User(
        username="employee2_leave_test",
        email="emp2leave@test.com",
        password_hash=get_password_hash("secret"),
        full_name="Test Employee 2",
        role_system=RoleSystem.EMPLOYEE,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    token = create_access_token(data={"sub": user.username})
    return {"Authorization": f"Bearer {token}"}


# ══════════════════════════════════════════════════════════════════════════════
# EMPLOYEE TESTS
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_employee_create_leave_request_success(client: AsyncClient, employee_headers: dict):
    """Employee creates a valid future leave request → 201."""
    payload = {"start_date": _in_days(1), "end_date": _in_days(3), "reason": "Vacation"}
    resp = await client.post("/employee/leave-requests", json=payload, headers=employee_headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "PENDING"
    assert data["reason"] == "Vacation"
    assert data["user_name"] == "Test Employee"


@pytest.mark.asyncio
async def test_employee_list_own_leave_requests(client: AsyncClient, employee_headers: dict):
    """Employee lists their own leave requests and sees them."""
    payload = {"start_date": _in_days(1), "end_date": _in_days(2)}
    await client.post("/employee/leave-requests", json=payload, headers=employee_headers)

    resp = await client.get("/employee/leave-requests", headers=employee_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_employee_cancel_pending_request(client: AsyncClient, employee_headers: dict):
    """Employee cancels a PENDING request → status becomes CANCELLED."""
    payload = {"start_date": _in_days(5), "end_date": _in_days(6)}
    create_resp = await client.post("/employee/leave-requests", json=payload, headers=employee_headers)
    assert create_resp.status_code == 201
    request_id = create_resp.json()["id"]

    cancel_resp = await client.delete(f"/employee/leave-requests/{request_id}", headers=employee_headers)
    assert cancel_resp.status_code == 200

    list_resp = await client.get("/employee/leave-requests?status=CANCELLED", headers=employee_headers)
    ids = [r["id"] for r in list_resp.json()]
    assert request_id in ids


@pytest.mark.asyncio
async def test_employee_cannot_cancel_already_cancelled(client: AsyncClient, employee_headers: dict):
    """Employee cannot cancel an already-cancelled request → 400."""
    payload = {"start_date": _in_days(7), "end_date": _in_days(8)}
    req_id = (await client.post("/employee/leave-requests", json=payload, headers=employee_headers)).json()["id"]

    await client.delete(f"/employee/leave-requests/{req_id}", headers=employee_headers)
    resp = await client.delete(f"/employee/leave-requests/{req_id}", headers=employee_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_employee_past_date_rejected(client: AsyncClient, employee_headers: dict):
    """start_date in the past → 400."""
    payload = {"start_date": _yesterday(), "end_date": _yesterday()}
    resp = await client.post("/employee/leave-requests", json=payload, headers=employee_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_employee_end_before_start_rejected(client: AsyncClient, employee_headers: dict):
    """end_date < start_date → 422 (Pydantic model_validator)."""
    payload = {"start_date": _in_days(5), "end_date": _in_days(2)}
    resp = await client.post("/employee/leave-requests", json=payload, headers=employee_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_employee_overlap_rejected(client: AsyncClient, employee_headers: dict):
    """Creating overlapping PENDING requests → 400."""
    payload1 = {"start_date": _in_days(10), "end_date": _in_days(14)}
    await client.post("/employee/leave-requests", json=payload1, headers=employee_headers)

    payload2 = {"start_date": _in_days(12), "end_date": _in_days(16)}
    resp = await client.post("/employee/leave-requests", json=payload2, headers=employee_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_no_overlap_between_different_employees(
    client: AsyncClient, employee_headers: dict, employee2_headers: dict
):
    """Same date range for two different employees → both 201."""
    payload = {"start_date": _in_days(20), "end_date": _in_days(22)}
    r1 = await client.post("/employee/leave-requests", json=payload, headers=employee_headers)
    r2 = await client.post("/employee/leave-requests", json=payload, headers=employee2_headers)
    assert r1.status_code == 201
    assert r2.status_code == 201


# ══════════════════════════════════════════════════════════════════════════════
# MANAGER TESTS
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_manager_list_all_leave_requests(
    client: AsyncClient, employee_headers: dict, auth_headers: dict
):
    """Manager can see all employees' leave requests."""
    await client.post("/employee/leave-requests",
                      json={"start_date": _in_days(1), "end_date": _in_days(2)},
                      headers=employee_headers)

    resp = await client.get("/manager/leave-requests", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_manager_approve_changes_status(
    client: AsyncClient, employee_headers: dict, auth_headers: dict
):
    """Manager approves → status is APPROVED."""
    req_id = (await client.post(
        "/employee/leave-requests",
        json={"start_date": _in_days(5), "end_date": _in_days(6)},
        headers=employee_headers
    )).json()["id"]

    approve_resp = await client.post(f"/manager/leave-requests/{req_id}/approve", headers=auth_headers)
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    list_resp = await client.get("/manager/leave-requests?status=APPROVED", headers=auth_headers)
    ids = [r["id"] for r in list_resp.json()]
    assert req_id in ids


@pytest.mark.asyncio
async def test_manager_approve_creates_unavailable_availability(
    client: AsyncClient,
    employee_headers: dict,
    auth_headers: dict,
    shift_definition,
    session: Session,
):
    """CRITICAL: Approval auto-creates UNAVAILABLE Availability for each (date, shift)."""
    from sqlmodel import select
    from app.models import Availability, AvailabilityStatus

    start = _in_days(30)
    end   = _in_days(31)

    req_id = (await client.post(
        "/employee/leave-requests",
        json={"start_date": start, "end_date": end},
        headers=employee_headers
    )).json()["id"]

    await client.post(f"/manager/leave-requests/{req_id}/approve", headers=auth_headers)

    unavailable = session.exec(
        select(Availability).where(Availability.status == AvailabilityStatus.UNAVAILABLE)
    ).all()
    # 2 days × 1 shift → at least 2 records
    assert len(unavailable) >= 2


@pytest.mark.asyncio
async def test_manager_reject_does_not_create_availability(
    client: AsyncClient,
    employee_headers: dict,
    auth_headers: dict,
    shift_definition,
    session: Session,
):
    """Rejection → no UNAVAILABLE availability created for the period."""
    from sqlmodel import select
    from app.models import Availability, AvailabilityStatus
    from datetime import date as dt

    start_str = _in_days(40)
    end_str   = _in_days(41)

    req_id = (await client.post(
        "/employee/leave-requests",
        json={"start_date": start_str, "end_date": end_str},
        headers=employee_headers
    )).json()["id"]

    reject_resp = await client.post(f"/manager/leave-requests/{req_id}/reject", headers=auth_headers)
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"

    s = dt.fromisoformat(start_str)
    e = dt.fromisoformat(end_str)
    unavailable_in_range = session.exec(
        select(Availability).where(
            Availability.status == AvailabilityStatus.UNAVAILABLE,
            Availability.date >= s,
            Availability.date <= e,
        )
    ).all()
    assert len(unavailable_in_range) == 0


@pytest.mark.asyncio
async def test_manager_cannot_approve_already_approved(
    client: AsyncClient, employee_headers: dict, auth_headers: dict
):
    """Double-approve → 400."""
    req_id = (await client.post(
        "/employee/leave-requests",
        json={"start_date": _in_days(50), "end_date": _in_days(51)},
        headers=employee_headers
    )).json()["id"]

    await client.post(f"/manager/leave-requests/{req_id}/approve", headers=auth_headers)
    resp = await client.post(f"/manager/leave-requests/{req_id}/approve", headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_manager_leave_calendar(
    client: AsyncClient, employee_headers: dict, auth_headers: dict
):
    """Calendar endpoint returns approved leave entries for the given month."""
    start = date.today() + timedelta(days=60)
    end   = start + timedelta(days=2)

    req_id = (await client.post(
        "/employee/leave-requests",
        json={"start_date": start.isoformat(), "end_date": end.isoformat()},
        headers=employee_headers
    )).json()["id"]

    await client.post(f"/manager/leave-requests/{req_id}/approve", headers=auth_headers)

    resp = await client.get(
        f"/manager/leave-requests/calendar?year={start.year}&month={start.month}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "entries" in data
    assert any(e["status"] == "APPROVED" for e in data["entries"])
