"""Google Calendar sync: background workers, triggers, RFC3339 windows, token handling, logging."""
import logging
import uuid
from datetime import date, time, timedelta

import httpx
import pytest
from httpx import AsyncClient
from sqlmodel import Session, select

from app.models import (
    GiveawayStatus, JobRole, RoleSystem, Schedule, ShiftDefinition, ShiftGiveaway, User,
)
from app.services import google_calendar_service as gcs
from app.services.google_calendar_service import GoogleCalendarService
from app.auth_utils import create_access_token


class Resp:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = str(self._json)

    def json(self):
        return self._json


@pytest.fixture
def gcal_http(monkeypatch):
    """Records every Google API call. `responses` can override per-method status codes."""
    calls = {"post": [], "put": [], "delete": [], "token": []}
    state = {"post_status": [200], "put_status": 200, "delete_status": 204, "tokeninfo": [200]}

    def _get(url, **kw):
        status = state["tokeninfo"].pop(0) if len(state["tokeninfo"]) > 1 else state["tokeninfo"][0]
        return Resp(status, {"aud": "x"})

    def _post(url, **kw):
        if "oauth2.googleapis.com/token" in url:
            calls["token"].append(kw)
            return Resp(200, {"access_token": "ya29.refreshed"})
        calls["post"].append({"url": url, **kw})
        status = state["post_status"].pop(0) if len(state["post_status"]) > 1 else state["post_status"][0]
        return Resp(status, {"id": "e"})

    def _put(url, **kw):
        calls["put"].append({"url": url, **kw})
        return Resp(state["put_status"], {"id": "e"})

    def _delete(url, **kw):
        calls["delete"].append({"url": url, **kw})
        return Resp(state["delete_status"])

    monkeypatch.setattr(httpx, "get", _get)
    monkeypatch.setattr(httpx, "post", _post)
    monkeypatch.setattr(httpx, "put", _put)
    monkeypatch.setattr(httpx, "delete", _delete)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "csecret")
    return calls, state


@pytest.fixture
def world(session: Session, test_tenant):
    """Manager + two employees (both with Google tokens), role and two shift definitions."""
    def mk(name, role_system=RoleSystem.EMPLOYEE, google=True):
        u = User(tenant_id=test_tenant.id, username=name, email=f"{name}@t.com", password_hash="h",
                 full_name=name.title(), role_system=role_system)
        if google:
            u.google_access_token = f"ya29.{name}"
            u.google_refresh_token = f"1//{name}"
        session.add(u)
        return u

    mgr = mk("mgr_cal", RoleSystem.MANAGER, google=False)
    e1 = mk("emp_one")
    e2 = mk("emp_two")
    role = JobRole(tenant_id=test_tenant.id, name="Kelner", color_hex="#fff")
    day = ShiftDefinition(tenant_id=test_tenant.id, name="Poranna", start_time=time(8, 0), end_time=time(16, 0))
    night = ShiftDefinition(tenant_id=test_tenant.id, name="Nocna", start_time=time(22, 0), end_time=time(6, 0))
    session.add_all([role, day, night])
    session.commit()
    for o in (mgr, e1, e2, role, day, night):
        session.refresh(o)

    def headers(u):
        return {"Authorization": "Bearer " + create_access_token(
            {"sub": u.username, "tenant_id": str(u.tenant_id)})}

    return dict(mgr=mgr, e1=e1, e2=e2, role=role, day=day, night=night,
                mgr_h=headers(mgr), e1_h=headers(e1), e2_h=headers(e2), tenant=test_tenant)


def _sched(session, w, user, d=None, shift="day", published=True):
    s = Schedule(date=d or date.today() + timedelta(days=3), shift_def_id=w[shift].id,
                 user_id=user.id, role_id=w["role"].id, is_published=published)
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


# ── OAuth consent URL ─────────────────────────────────────────────────────────

def test_authorization_url_requests_offline_access_and_consent(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-123")
    url = gcs.build_authorization_url()
    assert "access_type=offline" in url
    assert "prompt=consent" in url
    assert "calendar.events" in url
    assert "client_id=client-123" in url


def test_authorization_url_requires_client_id(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    with pytest.raises(ValueError):
        gcs.build_authorization_url()


# ── RFC3339 / time zone ───────────────────────────────────────────────────────

def test_event_window_rfc3339_with_offsets():
    # Summer (CEST, +02:00) and winter (CET, +01:00) - a fixed offset would get one of them wrong
    s, e = gcs.compute_event_window(date(2026, 7, 10), time(8, 0), time(16, 0))
    assert s.isoformat() == "2026-07-10T08:00:00+02:00"
    assert e.isoformat() == "2026-07-10T16:00:00+02:00"
    s, e = gcs.compute_event_window(date(2026, 1, 15), time(8, 0), time(16, 0))
    assert s.isoformat() == "2026-01-15T08:00:00+01:00"


def test_event_window_midnight_crossing_ends_next_day():
    s, e = gcs.compute_event_window(date(2026, 1, 15), time(22, 0), time(6, 0))
    assert e.date() == date(2026, 1, 16)
    assert e > s


def test_event_body_has_timezone_and_offset(session, world, gcal_http):
    calls, _ = gcal_http
    sched = _sched(session, world, world["e1"], date(2026, 1, 15), "night")
    assert GoogleCalendarService(session).sync_schedule_to_calendar(world["e1"], sched) is True
    body = calls["post"][0]["json"]
    assert body["start"]["timeZone"] == "Europe/Warsaw"
    assert body["start"]["dateTime"] == "2026-01-15T22:00:00+01:00"
    assert body["end"]["dateTime"] == "2026-01-16T06:00:00+01:00"
    assert "Stanowisko: Kelner" in body["description"] and "Nocna" in body["description"]


# ── token refresh & error logging ─────────────────────────────────────────────

def test_401_forces_token_refresh_and_retries(session, world, gcal_http):
    calls, state = gcal_http
    state["post_status"] = [401, 200]
    sched = _sched(session, world, world["e1"])
    assert GoogleCalendarService(session).sync_schedule_to_calendar(world["e1"], sched) is True
    assert len(calls["token"]) == 1
    assert calls["post"][1]["headers"]["Authorization"] == "Bearer ya29.refreshed"


def test_expired_token_without_refresh_token_logs_error(session, world, gcal_http, caplog):
    _, state = gcal_http
    state["tokeninfo"] = [400]
    user = world["e1"]
    user.google_refresh_token = None
    session.add(user)
    session.commit()
    sched = _sched(session, world, user)
    with caplog.at_level(logging.ERROR):
        assert GoogleCalendarService(session).sync_schedule_to_calendar(user, sched) is False
    assert "NO refresh token" in caplog.text


def test_api_error_is_logged_not_swallowed(session, world, gcal_http, caplog):
    _, state = gcal_http
    state["post_status"] = [500]
    sched = _sched(session, world, world["e1"])
    with caplog.at_level(logging.ERROR):
        assert GoogleCalendarService(session).sync_schedule_to_calendar(world["e1"], sched) is False
    assert "Google Calendar API error 500" in caplog.text


def test_exception_is_logged_with_traceback(session, world, gcal_http, monkeypatch, caplog):
    def boom(*a, **k):
        raise RuntimeError("network down")
    monkeypatch.setattr(httpx, "post", boom)
    sched = _sched(session, world, world["e1"])
    with caplog.at_level(logging.ERROR):
        assert GoogleCalendarService(session).sync_schedule_to_calendar(world["e1"], sched) is False
    assert "network down" in caplog.text


# ── background workers (primitive args, own session, tenant filter) ───────────

def test_sync_task_takes_primitive_ids_only(session, world, gcal_http):
    calls, _ = gcal_http
    sched = _sched(session, world, world["e1"])
    gcs.sync_schedule_task(sched.id, world["e1"].id, world["tenant"].id)
    assert len(calls["post"]) == 1
    assert f"plannerv2{sched.id.hex}" == calls["post"][0]["json"]["id"]


def test_sync_task_uses_independent_session(session, world, gcal_http, monkeypatch):
    opened = []
    from contextlib import contextmanager

    @contextmanager
    def tracking():
        opened.append(1)
        yield session
    monkeypatch.setattr(gcs, "background_session", tracking)
    sched = _sched(session, world, world["e1"])
    gcs.sync_schedule_task(sched.id, world["e1"].id, world["tenant"].id)
    assert opened == [1]


def test_sync_task_refuses_foreign_tenant(session, world, gcal_http):
    calls, _ = gcal_http
    sched = _sched(session, world, world["e1"])
    gcs.sync_schedule_task(sched.id, world["e1"].id, world["tenant"].id + 999)
    assert calls["post"] == []


def test_sync_task_never_raises(session, world, gcal_http, monkeypatch):
    monkeypatch.setattr(gcs, "background_session", lambda: (_ for _ in ()).throw(RuntimeError("db down")))
    gcs.sync_schedule_task(uuid.uuid4(), uuid.uuid4(), 1)  # must not propagate


def test_unpublished_schedule_is_not_synced(session, world, gcal_http):
    calls, _ = gcal_http
    sched = _sched(session, world, world["e1"], published=False)
    gcs.sync_schedule_task(sched.id, world["e1"].id, world["tenant"].id)
    assert calls["post"] == []


# ── triggers ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_manual_assignment_update_syncs_and_delete_removes(client: AsyncClient, session, world, gcal_http):
    calls, _ = gcal_http
    sched = _sched(session, world, world["e1"])  # published
    r = await client.post("/scheduler/assignment", headers=world["mgr_h"], json={
        "date": str(sched.date), "shift_def_id": world["night"].id,
        "user_id": str(world["e1"].id), "role_id": world["role"].id})
    assert r.json()["status"] == "updated"
    assert len(calls["post"]) == 1
    assert calls["post"][0]["json"]["end"]["dateTime"].startswith(str(sched.date + timedelta(days=1)))

    r = await client.delete(f"/scheduler/assignment/{sched.id}", headers=world["mgr_h"])
    assert r.json()["status"] == "deleted"
    assert len(calls["delete"]) == 1 and sched.id.hex in calls["delete"][0]["url"]


@pytest.mark.asyncio
async def test_save_batch_replaces_events(client: AsyncClient, session, world, gcal_http):
    calls, _ = gcal_http
    old = _sched(session, world, world["e1"], date(2026, 11, 2))
    r = await client.post("/scheduler/save_batch", headers=world["mgr_h"], json={
        "start_date": "2026-11-02", "end_date": "2026-11-03",
        "is_published": True,
        "items": [{"date": "2026-11-03", "shift_def_id": world["day"].id,
                   "user_id": str(world["e2"].id), "role_id": world["role"].id}]})
    assert r.status_code == 200
    # stale event of the removed schedule is deleted, the new schedule is created for e2
    assert any(old.id.hex in c["url"] for c in calls["delete"])
    assert len(calls["post"]) == 1
    assert calls["post"][0]["headers"]["Authorization"] == "Bearer ya29.emp_two"


@pytest.mark.asyncio
async def test_publish_syncs_after_commit(client: AsyncClient, session, world, gcal_http):
    calls, _ = gcal_http
    draft = _sched(session, world, world["e1"], date(2026, 11, 5), published=False)
    r = await client.post("/scheduler/publish?start_date=2026-11-01&end_date=2026-11-30", headers=world["mgr_h"])
    assert r.json()["count"] == 1
    assert len(calls["post"]) == 1
    assert calls["post"][0]["json"]["id"] == f"plannerv2{draft.id.hex}"


@pytest.mark.asyncio
async def test_shift_definition_update_resyncs_upcoming_events(client: AsyncClient, session, world, gcal_http):
    calls, _ = gcal_http
    _sched(session, world, world["e1"])
    _sched(session, world, world["e2"], date.today() + timedelta(days=4))
    r = await client.put(f"/manager/shifts/{world['day'].id}", headers=world["mgr_h"], json={
        "name": "Poranna", "start_time": "09:00", "end_time": "17:00", "applicable_days": [0, 1, 2, 3, 4, 5, 6]})
    assert r.status_code == 200
    assert len(calls["post"]) == 2
    assert all("T09:00:00" in c["json"]["start"]["dateTime"] for c in calls["post"])


@pytest.mark.asyncio
async def test_claim_giveaway_moves_event_between_users(client: AsyncClient, session, world, gcal_http):
    calls, _ = gcal_http
    sched = _sched(session, world, world["e1"])
    g = ShiftGiveaway(schedule_id=sched.id, offered_by=world["e1"].id, status=GiveawayStatus.OPEN)
    session.add(g)
    session.commit()
    r = await client.post(f"/employee/giveaways/{g.id}/claim", headers=world["e2_h"])
    assert r.status_code == 200
    assert len(calls["delete"]) == 1
    assert calls["delete"][0]["headers"]["Authorization"] == "Bearer ya29.emp_one"
    assert len(calls["post"]) == 1
    assert calls["post"][0]["headers"]["Authorization"] == "Bearer ya29.emp_two"


@pytest.mark.asyncio
async def test_manager_reassign_runs_in_background_and_moves_event(client: AsyncClient, session, world, gcal_http):
    calls, _ = gcal_http
    sched = _sched(session, world, world["e1"])
    g = ShiftGiveaway(schedule_id=sched.id, offered_by=world["e1"].id, status=GiveawayStatus.OPEN)
    session.add(g)
    session.commit()
    r = await client.post(f"/manager/giveaways/{g.id}/reassign", headers=world["mgr_h"],
                          json={"new_user_id": str(world["e2"].id)})
    assert r.status_code == 200 and r.json()["status"] == "reassigned"
    assert len(calls["delete"]) == 1 and len(calls["post"]) == 1
    session.refresh(sched)
    assert sched.user_id == world["e2"].id
