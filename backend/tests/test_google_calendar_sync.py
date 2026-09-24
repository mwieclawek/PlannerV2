import uuid
import pytest
from datetime import date, time, datetime, timedelta
from httpx import AsyncClient
from sqlmodel import Session

from app.models import User, Schedule, ShiftDefinition, JobRole, RoleSystem, RestaurantConfig, ShiftGiveaway, GiveawayStatus
from app.services.google_calendar_service import GoogleCalendarService, WARSAW_TZ


class MockHttpxResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = str(self._json_data)

    def json(self):
        return self._json_data


@pytest.fixture
def test_user_with_token(session: Session) -> User:
    user = User(
        username="test_sync_user",
        email="test_sync@example.com",
        password_hash="hash",
        full_name="Jan Kowalski",
        role_system=RoleSystem.EMPLOYEE,
        is_active=True
    )
    user.google_access_token = "ya29.test_valid_access_token"
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def shift_def_day(session: Session) -> ShiftDefinition:
    s = ShiftDefinition(name="Poranna", start_time=time(8, 0), end_time=time(16, 0))
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


@pytest.fixture
def test_job_role(session: Session) -> JobRole:
    r = JobRole(name="Kelner", color_hex="#2196F3")
    session.add(r)
    session.commit()
    session.refresh(r)
    return r


@pytest.fixture
def shift_def_night(session: Session) -> ShiftDefinition:
    s = ShiftDefinition(name="Nocna", start_time=time(20, 0), end_time=time(4, 0))
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


def test_deterministic_event_id(session: Session, test_user_with_token: User, shift_def_day: ShiftDefinition, test_job_role: JobRole):
    sched = Schedule(
        date=date(2026, 9, 25),
        shift_def_id=shift_def_day.id,
        user_id=test_user_with_token.id,
        role_id=test_job_role.id,
        is_published=True
    )
    session.add(sched)
    session.commit()
    session.refresh(sched)

    expected_id = f"plannerv2{sched.id.hex}"
    assert expected_id.isalnum()
    assert expected_id.islower()
    assert len(expected_id) == len("plannerv2") + 32


def test_sync_schedule_to_calendar(session: Session, test_user_with_token: User, shift_def_day: ShiftDefinition, test_job_role: JobRole, monkeypatch):
    sched = Schedule(
        date=date(2026, 9, 25),
        shift_def_id=shift_def_day.id,
        user_id=test_user_with_token.id,
        role_id=test_job_role.id,
        is_published=True
    )
    session.add(sched)
    session.commit()
    session.refresh(sched)


    captured_requests = []

    import httpx
    def mock_get(url, **kwargs):
        # Tokeninfo call
        if "tokeninfo" in url:
            return MockHttpxResponse(200, {"aud": "test"})
        return MockHttpxResponse(404)

    def mock_post(url, **kwargs):
        captured_requests.append({"url": url, "kwargs": kwargs})
        return MockHttpxResponse(200, {"id": "mock_id"})

    monkeypatch.setattr(httpx, "get", mock_get)
    monkeypatch.setattr(httpx, "post", mock_post)

    service = GoogleCalendarService(session)
    result = service.sync_schedule_to_calendar(test_user_with_token, sched)

    assert result is True
    assert len(captured_requests) == 1
    req = captured_requests[0]
    expected_event_id = f"plannerv2{sched.id.hex}"
    
    body = req["kwargs"]["json"]
    assert body["id"] == expected_event_id
    assert "Zmiana" in body["summary"]
    assert "Poranna" in body["description"]
    assert "2026-09-25T08:00:00" in body["start"]["dateTime"]
    assert "2026-09-25T16:00:00" in body["end"]["dateTime"]


def test_sync_night_shift_crosses_midnight(session: Session, test_user_with_token: User, shift_def_night: ShiftDefinition, test_job_role: JobRole, monkeypatch):
    sched = Schedule(
        date=date(2026, 9, 25),
        shift_def_id=shift_def_night.id,
        user_id=test_user_with_token.id,
        role_id=test_job_role.id,
        is_published=True
    )
    session.add(sched)
    session.commit()
    session.refresh(sched)


    captured_requests = []

    import httpx
    def mock_get(url, **kwargs):
        return MockHttpxResponse(200, {"aud": "test"})

    def mock_post(url, **kwargs):
        captured_requests.append({"url": url, "kwargs": kwargs})
        return MockHttpxResponse(200, {"id": "mock_id"})

    monkeypatch.setattr(httpx, "get", mock_get)
    monkeypatch.setattr(httpx, "post", mock_post)

    service = GoogleCalendarService(session)
    result = service.sync_schedule_to_calendar(test_user_with_token, sched)

    assert result is True
    body = captured_requests[0]["kwargs"]["json"]
    assert "2026-09-25T20:00:00" in body["start"]["dateTime"]
    # Night shift ends next day: 2026-09-26
    assert "2026-09-26T04:00:00" in body["end"]["dateTime"]


def test_delete_calendar_event(session: Session, test_user_with_token: User, monkeypatch):
    fake_schedule_id = uuid.uuid4()
    captured_requests = []

    import httpx
    def mock_get(url, **kwargs):
        return MockHttpxResponse(200, {"aud": "test"})

    def mock_delete(url, **kwargs):
        captured_requests.append({"url": url, "kwargs": kwargs})
        return MockHttpxResponse(204)

    monkeypatch.setattr(httpx, "get", mock_get)
    monkeypatch.setattr(httpx, "delete", mock_delete)

    service = GoogleCalendarService(session)
    result = service.delete_calendar_event(test_user_with_token, fake_schedule_id)

    assert result is True
    assert len(captured_requests) == 1
    assert f"plannerv2{fake_schedule_id.hex}" in captured_requests[0]["url"]


@pytest.mark.asyncio
async def test_employee_sync_endpoint(client: AsyncClient, employee_headers: dict, monkeypatch):
    import httpx

    def mock_get(url, **kwargs):
        return MockHttpxResponse(200, {"aud": "test"})

    def mock_post(url, **kwargs):
        return MockHttpxResponse(200, {"id": "mock_event"})

    monkeypatch.setattr(httpx, "get", mock_get)
    monkeypatch.setattr(httpx, "post", mock_post)

    response = await client.post(
        "/employee/google-calendar/sync",
        headers=employee_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "synced" in data
    assert "status" in data


def test_sync_schedule_summary_with_restaurant_config(session: Session, test_user_with_token: User, shift_def_day: ShiftDefinition, test_job_role: JobRole, monkeypatch):
    config = session.get(RestaurantConfig, 1)
    if not config:
        config = RestaurantConfig(id=1, name="Trattoria Test")
        session.add(config)
    else:
        config.name = "Trattoria Test"
        session.add(config)
    session.commit()

    sched = Schedule(
        date=date(2026, 9, 25),
        shift_def_id=shift_def_day.id,
        user_id=test_user_with_token.id,
        role_id=test_job_role.id,
        is_published=True
    )
    session.add(sched)
    session.commit()
    session.refresh(sched)

    captured_requests = []
    import httpx
    monkeypatch.setattr(httpx, "get", lambda url, **kw: MockHttpxResponse(200, {"aud": "test"}))
    monkeypatch.setattr(httpx, "post", lambda url, **kw: (captured_requests.append(kw), MockHttpxResponse(200))[1])

    service = GoogleCalendarService(session)
    result = service.sync_schedule_to_calendar(test_user_with_token, sched)
    assert result is True
    assert len(captured_requests) == 1
    body = captured_requests[0]["json"]
    assert body["summary"] == "Zmiana Trattoria Test"
    assert "Poranna" in body["description"]


@pytest.mark.asyncio
async def test_claim_giveaway_syncs_calendars(client: AsyncClient, session: Session, employee_headers: dict, shift_def_day: ShiftDefinition, test_job_role: JobRole, monkeypatch):
    giver = User(
        username="giver_user",
        email="giver@example.com",
        password_hash="hash",
        full_name="Adam Giver",
        role_system=RoleSystem.EMPLOYEE,
        is_active=True
    )
    giver.google_access_token = "ya29.giver_token"
    session.add(giver)
    session.commit()
    session.refresh(giver)

    sched = Schedule(
        date=date(2026, 9, 28),
        shift_def_id=shift_def_day.id,
        user_id=giver.id,
        role_id=test_job_role.id,
        is_published=True
    )
    session.add(sched)
    session.commit()
    session.refresh(sched)

    giveaway = ShiftGiveaway(
        schedule_id=sched.id,
        offered_by=giver.id,
        status=GiveawayStatus.OPEN
    )
    session.add(giveaway)
    session.commit()
    session.refresh(giveaway)

    deleted_urls = []
    put_urls = []
    import httpx
    monkeypatch.setattr(httpx, "get", lambda url, **kw: MockHttpxResponse(200, {"aud": "test"}))
    monkeypatch.setattr(httpx, "delete", lambda url, **kw: (deleted_urls.append(url), MockHttpxResponse(204))[1])
    monkeypatch.setattr(httpx, "put", lambda url, **kw: (put_urls.append(url), MockHttpxResponse(200))[1])

    response = await client.post(f"/employee/giveaways/{giveaway.id}/claim", headers=employee_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "claimed"

    assert len(deleted_urls) == 1
    assert f"plannerv2{sched.id.hex}" in deleted_urls[0]


def test_manager_reassign_giveaway_syncs_calendars(session: Session, shift_def_day: ShiftDefinition, test_job_role: JobRole, monkeypatch):
    from app.services.manager_service import ManagerService
    user1 = User(
        username="m_giver",
        email="m_giver@example.com",
        password_hash="hash",
        full_name="Jan Giver",
        role_system=RoleSystem.EMPLOYEE,
        is_active=True
    )
    user1.google_access_token = "ya29.user1"

    user2 = User(
        username="m_taker",
        email="m_taker@example.com",
        password_hash="hash",
        full_name="Anna Taker",
        role_system=RoleSystem.EMPLOYEE,
        is_active=True
    )
    user2.google_access_token = "ya29.user2"
    session.add_all([user1, user2])
    session.commit()

    sched = Schedule(
        date=date(2026, 9, 29),
        shift_def_id=shift_def_day.id,
        user_id=user1.id,
        role_id=test_job_role.id,
        is_published=True
    )
    session.add(sched)
    session.commit()

    giveaway = ShiftGiveaway(
        schedule_id=sched.id,
        offered_by=user1.id,
        status=GiveawayStatus.OPEN
    )
    session.add(giveaway)
    session.commit()

    deleted_urls = []
    post_urls = []
    import httpx
    monkeypatch.setattr(httpx, "get", lambda url, **kw: MockHttpxResponse(200, {"aud": "test"}))
    monkeypatch.setattr(httpx, "delete", lambda url, **kw: (deleted_urls.append(url), MockHttpxResponse(204))[1])
    monkeypatch.setattr(httpx, "post", lambda url, **kw: (post_urls.append(url), MockHttpxResponse(200))[1])

    mgr_svc = ManagerService(session)
    res = mgr_svc.reassign_giveaway(giveaway.id, user2.id)
    assert res["status"] == "reassigned"
    assert len(deleted_urls) == 1
    assert f"plannerv2{sched.id.hex}" in deleted_urls[0]
    assert len(post_urls) == 1


def test_sync_schedule_updates_on_conflict(session: Session, test_user_with_token: User, shift_def_day: ShiftDefinition, test_job_role: JobRole, monkeypatch):
    sched = Schedule(
        date=date(2026, 9, 25),
        shift_def_id=shift_def_day.id,
        user_id=test_user_with_token.id,
        role_id=test_job_role.id,
        is_published=True
    )
    session.add(sched)
    session.commit()
    session.refresh(sched)

    captured_put = []
    import httpx
    monkeypatch.setattr(httpx, "get", lambda url, **kw: MockHttpxResponse(200, {"aud": "test"}))
    monkeypatch.setattr(httpx, "post", lambda url, **kw: MockHttpxResponse(409, {"error": "duplicate"}))
    monkeypatch.setattr(httpx, "put", lambda url, **kw: (captured_put.append({"url": url, "kwargs": kw}), MockHttpxResponse(200, {"id": "mock_id"}))[1])

    service = GoogleCalendarService(session)
    result = service.sync_schedule_to_calendar(test_user_with_token, sched)
    assert result is True
    assert len(captured_put) == 1
    assert f"plannerv2{sched.id.hex}" in captured_put[0]["url"]
    assert captured_put[0]["kwargs"]["json"]["status"] == "confirmed"


