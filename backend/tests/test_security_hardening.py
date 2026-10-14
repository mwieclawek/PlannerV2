"""Security hardening: tenant isolation (IDOR), mass assignment, token leakage, inactive users,
FCM cleanup, input limits and proxy configuration."""
import os
import uuid
from datetime import date, time, timedelta

import pytest
from httpx import AsyncClient
from sqlmodel import Session, select

from app.auth_utils import create_access_token
from app.models import (
    Attendance, GiveawayStatus, JobRole, LeaveRequest, LeaveStatus, Notification, RestaurantConfig,
    RoleSystem, Schedule, ShiftDefinition, ShiftGiveaway, User, UserDevice,
)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _headers(u: User) -> dict:
    return {"Authorization": "Bearer " + create_access_token({"sub": u.username, "tenant_id": str(u.tenant_id)})}


@pytest.fixture
def two_tenants(session: Session, test_tenant):
    """Tenant A = conftest 'test' restaurant (manager + employee). Tenant B = foreign data."""
    other = RestaurantConfig(name="Other Restaurant", slug="other")
    session.add(other)
    session.commit()
    session.refresh(other)

    def mk(tenant, name, role=RoleSystem.EMPLOYEE):
        u = User(tenant_id=tenant.id, username=name, email=f"{name}@x.com", password_hash="h",
                 full_name=name, role_system=role)
        session.add(u)
        return u

    mgr_a, emp_a = mk(test_tenant, "mgr_a", RoleSystem.MANAGER), mk(test_tenant, "emp_a")
    mgr_b, emp_b = mk(other, "mgr_b", RoleSystem.MANAGER), mk(other, "emp_b")
    emp_b2 = mk(other, "emp_b2")
    role_b = JobRole(tenant_id=other.id, name="B-role", color_hex="#000")
    shift_b = ShiftDefinition(tenant_id=other.id, name="B-shift", start_time=time(8), end_time=time(16))
    session.add_all([role_b, shift_b])
    session.commit()
    for o in (mgr_a, emp_a, mgr_b, emp_b, emp_b2, role_b, shift_b):
        session.refresh(o)

    sched_b = Schedule(date=date.today() + timedelta(days=2), shift_def_id=shift_b.id, user_id=emp_b.id,
                       role_id=role_b.id, is_published=True)
    session.add(sched_b)
    session.commit()
    session.refresh(sched_b)
    give_b = ShiftGiveaway(schedule_id=sched_b.id, offered_by=emp_b.id, status=GiveawayStatus.OPEN)
    leave_b = LeaveRequest(user_id=emp_b.id, start_date=date.today() + timedelta(days=10),
                           end_date=date.today() + timedelta(days=11), reason="x")
    att_b = Attendance(user_id=emp_b.id, date=date.today(), check_in=time(8), check_out=time(16))
    notif_b = Notification(user_id=emp_b.id, title="t", body="b")
    session.add_all([give_b, leave_b, att_b, notif_b])
    session.commit()
    for o in (give_b, leave_b, att_b, notif_b):
        session.refresh(o)
    return dict(mgr_a=mgr_a, emp_a=emp_a, emp_b=emp_b, emp_b2=emp_b2, sched_b=sched_b, give_b=give_b,
                leave_b=leave_b, att_b=att_b, notif_b=notif_b, role_b=role_b, shift_b=shift_b,
                mgr_h=_headers(mgr_a), emp_h=_headers(emp_a), tenant_b=other)


# ── Tenant isolation / IDOR ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_manager_cannot_touch_foreign_users(client: AsyncClient, session, two_tenants):
    t, h = two_tenants, two_tenants["mgr_h"]
    uid = t["emp_b"].id
    assert (await client.put(f"/manager/users/{uid}/password", headers=h,
                             json={"new_password": "NewPass123"})).status_code == 404
    assert (await client.put(f"/manager/users/{uid}", headers=h, json={"full_name": "Pwned"})).status_code == 404
    assert (await client.put(f"/manager/users/{uid}/roles", headers=h, json={"role_ids": []})).status_code == 404
    assert (await client.get(f"/manager/users/{uid}/stats", headers=h)).status_code == 404
    session.refresh(t["emp_b"])
    assert t["emp_b"].full_name == "emp_b" and t["emp_b"].password_hash == "h"


@pytest.mark.asyncio
async def test_manager_cannot_assign_foreign_role_or_shift(client: AsyncClient, session, two_tenants):
    t, h = two_tenants, two_tenants["mgr_h"]
    # own user but foreign role/shift
    r = await client.put(f"/manager/users/{t['emp_a'].id}/roles", headers=h, json={"role_ids": [t["role_b"].id]})
    assert r.status_code == 404
    assert (await client.put(f"/manager/roles/{t['role_b'].id}", headers=h,
                             json={"name": "x", "color_hex": "#111111"})).status_code == 404
    assert (await client.delete(f"/manager/roles/{t['role_b'].id}", headers=h)).status_code == 404
    assert (await client.put(f"/manager/shifts/{t['shift_b'].id}", headers=h, json={
        "name": "x", "start_time": "01:00", "end_time": "02:00", "applicable_days": [0]})).status_code == 404
    assert (await client.delete(f"/manager/shifts/{t['shift_b'].id}", headers=h)).status_code == 404
    r = await client.post("/scheduler/assignment", headers=h, json={
        "date": str(date.today()), "shift_def_id": t["shift_b"].id,
        "user_id": str(t["emp_a"].id), "role_id": t["role_b"].id})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_manager_cannot_schedule_or_delete_foreign_schedule(client: AsyncClient, session, two_tenants):
    t, h = two_tenants, two_tenants["mgr_h"]
    r = await client.post("/scheduler/assignment", headers=h, json={
        "date": str(date.today()), "shift_def_id": t["shift_b"].id,
        "user_id": str(t["emp_b"].id), "role_id": t["role_b"].id})
    assert r.status_code == 404
    r = await client.post("/scheduler/save_batch", headers=h, json={
        "start_date": str(date.today()), "end_date": str(date.today()),
        "items": [{"date": str(date.today()), "shift_def_id": t["shift_b"].id,
                   "user_id": str(t["emp_b"].id), "role_id": t["role_b"].id}]})
    assert r.status_code == 404
    r = await client.delete(f"/scheduler/assignment/{t['sched_b'].id}", headers=h)
    assert r.json()["status"] == "not_found"
    assert session.get(Schedule, t["sched_b"].id) is not None


@pytest.mark.asyncio
async def test_manager_cannot_touch_foreign_attendance_giveaway_leave(client: AsyncClient, session, two_tenants):
    t, h = two_tenants, two_tenants["mgr_h"]
    assert (await client.put(f"/manager/attendance/{t['att_b'].id}/confirm", headers=h)).status_code == 404
    assert (await client.put(f"/manager/attendance/{t['att_b'].id}/reject", headers=h)).status_code == 404
    r = await client.post("/manager/attendance", headers=h, json={
        "user_id": str(t["emp_b"].id), "date": str(date.today()), "check_in": "08:00:00", "check_out": "16:00:00"})
    assert r.status_code == 404
    assert (await client.post(f"/manager/giveaways/{t['give_b'].id}/reassign", headers=h,
                              json={"new_user_id": str(t["emp_b2"].id)})).status_code == 404
    assert (await client.delete(f"/manager/giveaways/{t['give_b'].id}", headers=h)).status_code == 404
    assert (await client.post(f"/manager/leave-requests/{t['leave_b'].id}/approve", headers=h)).status_code == 404
    assert (await client.post(f"/manager/leave-requests/{t['leave_b'].id}/reject", headers=h)).status_code == 404
    session.refresh(t["att_b"]); session.refresh(t["give_b"]); session.refresh(t["leave_b"])
    assert t["give_b"].status == GiveawayStatus.OPEN
    assert t["leave_b"].status == LeaveStatus.PENDING


@pytest.mark.asyncio
async def test_manager_cannot_reassign_own_giveaway_to_foreign_user(client: AsyncClient, session, two_tenants,
                                                                     test_tenant):
    t = two_tenants
    shift = ShiftDefinition(tenant_id=test_tenant.id, name="A", start_time=time(8), end_time=time(16))
    role = JobRole(tenant_id=test_tenant.id, name="A", color_hex="#fff")
    session.add_all([shift, role])
    session.commit()
    sched = Schedule(date=date.today() + timedelta(days=2), shift_def_id=shift.id, user_id=t["emp_a"].id,
                     role_id=role.id, is_published=True)
    session.add(sched)
    session.commit()
    g = ShiftGiveaway(schedule_id=sched.id, offered_by=t["emp_a"].id)
    session.add(g)
    session.commit()
    r = await client.post(f"/manager/giveaways/{g.id}/reassign", headers=t["mgr_h"],
                          json={"new_user_id": str(t["emp_b"].id)})
    assert r.status_code == 404
    session.refresh(sched)
    assert sched.user_id == t["emp_a"].id


@pytest.mark.asyncio
async def test_employee_cannot_claim_or_cancel_foreign_giveaway(client: AsyncClient, session, two_tenants):
    t = two_tenants
    assert (await client.post(f"/employee/giveaways/{t['give_b'].id}/claim", headers=t["emp_h"])).status_code == 404
    assert (await client.delete(f"/employee/giveaway/{t['give_b'].id}", headers=t["emp_h"])).status_code == 404
    assert (await client.delete(f"/employee/leave-requests/{t['leave_b'].id}", headers=t["emp_h"])).status_code == 404
    session.refresh(t["sched_b"])
    assert t["sched_b"].user_id == t["emp_b"].id


@pytest.mark.asyncio
async def test_notification_scoped_to_owner(client: AsyncClient, session, two_tenants):
    t = two_tenants
    r = await client.patch(f"/api/notifications/{t['notif_b'].id}/read", headers=t["emp_h"])
    assert r.status_code == 200
    session.refresh(t["notif_b"])
    assert t["notif_b"].is_read is False


@pytest.mark.asyncio
async def test_requirements_are_tenant_scoped(client: AsyncClient, session, two_tenants):
    t, h = two_tenants, two_tenants["mgr_h"]
    r = await client.post("/manager/requirements", headers=h, json=[{
        "date": str(date.today()), "shift_def_id": t["shift_b"].id, "role_id": t["role_b"].id, "min_count": 1}])
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_solver_ignores_foreign_tenant(session, two_tenants, test_tenant):
    from app.services.solver import SolverService
    from app.models import UserJobRoleLink
    t = two_tenants
    session.add(UserJobRoleLink(user_id=t["emp_b"].id, role_id=t["role_b"].id))
    session.commit()
    res = SolverService(session, tenant_id=test_tenant.id).solve(date.today(), date.today(), save=False)
    assert "emp_b" not in str(res)


@pytest.mark.asyncio
async def test_tenant_header_and_query_cannot_override_tenant(client: AsyncClient, two_tenants):
    t = two_tenants
    r = await client.get("/manager/users", headers={**t["mgr_h"], "X-Tenant-Slug": "other", "X-Tenant-Id": "999"},
                         params={"tenant_id": t["tenant_b"].id, "restaurant_id": t["tenant_b"].id})
    assert r.status_code == 200
    assert {u["username"] for u in r.json()} == {"emp_a"}


# ── Mass assignment ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_manager_update_user_cannot_set_superadmin_or_tenant(client: AsyncClient, session, two_tenants):
    t = two_tenants
    r = await client.put(f"/manager/users/{t['emp_a'].id}", headers=t["mgr_h"], json={
        "full_name": "Renamed", "is_superadmin": True, "tenant_id": t["tenant_b"].id,
        "restaurant_id": t["tenant_b"].id, "password_hash": "pwned", "id": str(uuid.uuid4()),
        "encrypted_google_access_token": "stolen"})
    assert r.status_code == 200
    session.refresh(t["emp_a"])
    assert t["emp_a"].full_name == "Renamed"
    assert t["emp_a"].is_superadmin is False
    assert t["emp_a"].tenant_id == t["mgr_a"].tenant_id
    assert t["emp_a"].password_hash == "h"
    assert t["emp_a"].encrypted_google_access_token is None


@pytest.mark.asyncio
async def test_manager_create_user_ignores_privileged_fields(client: AsyncClient, session, two_tenants):
    t = two_tenants
    r = await client.post("/manager/users", headers=t["mgr_h"], json={
        "username": "newbie", "password": "Passw0rdX", "full_name": "New Bie", "role_system": "EMPLOYEE",
        "is_superadmin": True, "tenant_id": t["tenant_b"].id, "restaurant_id": t["tenant_b"].id})
    assert r.status_code == 200
    user = session.exec(select(User).where(User.username == "newbie")).first()
    assert user.is_superadmin is False
    assert user.tenant_id == t["mgr_a"].tenant_id


def test_user_input_schemas_have_no_privileged_fields():
    from app.schemas import UserCreate, UserUpdate
    for schema in (UserCreate, UserUpdate):
        fields = set(schema.model_fields)
        assert not fields & {"is_superadmin", "tenant_id", "restaurant_id", "password_hash",
                             "encrypted_google_access_token", "encrypted_google_refresh_token"}


# ── Sensitive data in responses ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_responses_never_contain_tokens_or_hashes(client: AsyncClient, session, two_tenants):
    t = two_tenants
    t["emp_a"].google_access_token = "ya29.SECRET_ACCESS"
    t["emp_a"].google_refresh_token = "1//SECRET_REFRESH"
    session.add(t["emp_a"])
    session.commit()

    me = await client.get("/auth/me", headers=t["emp_h"])
    users = await client.get("/manager/users", headers=t["mgr_h"])
    upd = await client.put(f"/manager/users/{t['emp_a'].id}", headers=t["mgr_h"], json={"full_name": "E"})
    for resp in (me, users, upd):
        assert resp.status_code == 200
        text = resp.text
        for needle in ("SECRET_ACCESS", "SECRET_REFRESH", "password", "hashed", "google_access_token",
                       "google_refresh_token", "google_token_expiry", "encrypted_"):
            assert needle not in text, needle
    assert me.json()["is_google_calendar_connected"] is True
    assert users.json()[0]["is_google_calendar_connected"] is True


@pytest.mark.asyncio
async def test_google_connected_flag_false_without_tokens(client: AsyncClient, two_tenants):
    r = await client.get("/auth/me", headers=two_tenants["emp_h"])
    assert r.json()["is_google_calendar_connected"] is False


# ── Inactive users / FCM cleanup ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_inactive_user_with_valid_jwt_is_rejected(client: AsyncClient, session, two_tenants):
    t = two_tenants
    ok = await client.get("/auth/me", headers=t["emp_h"])
    assert ok.status_code == 200
    t["emp_a"].is_active = False
    session.add(t["emp_a"])
    session.commit()
    r = await client.get("/auth/me", headers=t["emp_h"])
    assert r.status_code == 403
    assert r.json()["detail"] == "Inactive user or tenant"


@pytest.mark.asyncio
async def test_inactive_tenant_is_rejected(client: AsyncClient, session, two_tenants, test_tenant):
    test_tenant.is_active = False
    session.add(test_tenant)
    session.commit()
    r = await client.get("/auth/me", headers=two_tenants["emp_h"])
    assert r.status_code == 403
    assert r.json()["detail"] == "Inactive user or tenant"


@pytest.mark.asyncio
async def test_deactivating_user_deletes_fcm_tokens(client: AsyncClient, session, two_tenants):
    t = two_tenants
    session.add_all([UserDevice(user_id=t["emp_a"].id, fcm_token="tok-1"),
                     UserDevice(user_id=t["emp_a"].id, fcm_token="tok-2"),
                     UserDevice(user_id=t["mgr_a"].id, fcm_token="tok-mgr")])
    session.commit()
    r = await client.put(f"/manager/users/{t['emp_a'].id}", headers=t["mgr_h"], json={"is_active": False})
    assert r.status_code == 200
    left = {d.fcm_token for d in session.exec(select(UserDevice)).all()}
    assert left == {"tok-mgr"}


@pytest.mark.asyncio
async def test_logout_unregisters_fcm_token(client: AsyncClient, session, two_tenants):
    t = two_tenants
    session.add_all([UserDevice(user_id=t["emp_a"].id, fcm_token="mine"),
                     UserDevice(user_id=t["emp_a"].id, fcm_token="other-device")])
    session.commit()
    r = await client.post("/auth/logout", headers=t["emp_h"], json={"fcm_token": "mine"})
    assert r.status_code == 200
    assert {d.fcm_token for d in session.exec(select(UserDevice)).all()} == {"other-device"}


@pytest.mark.asyncio
async def test_unregister_device_cannot_remove_foreign_token(client: AsyncClient, session, two_tenants):
    t = two_tenants
    session.add(UserDevice(user_id=t["emp_b"].id, fcm_token="b-token"))
    session.commit()
    await client.post("/api/notifications/devices/unregister", headers=t["emp_h"], json={"token": "b-token"})
    await client.delete("/api/notifications/devices/b-token", headers=t["emp_h"])
    assert session.exec(select(UserDevice).where(UserDevice.fcm_token == "b-token")).first() is not None


@pytest.mark.asyncio
async def test_blocking_restaurant_purges_device_tokens(client: AsyncClient, session, two_tenants):
    t = two_tenants
    sa = User(tenant_id=t["tenant_b"].id, username="root", email="root@x.com", password_hash="h",
              full_name="Root", role_system=RoleSystem.ADMIN, is_superadmin=True)
    session.add(sa)
    session.add(UserDevice(user_id=t["emp_b"].id, fcm_token="b-dev"))
    session.add(UserDevice(user_id=t["emp_a"].id, fcm_token="a-dev"))
    session.commit()
    r = await client.put(f"/sysadmin/restaurants/{t['tenant_b'].id}/status", headers=_headers(sa),
                         json={"is_active": False})
    assert r.status_code == 200
    assert {d.fcm_token for d in session.exec(select(UserDevice)).all()} == {"a-dev"}


# ── Secrets ───────────────────────────────────────────────────────────────────

def test_production_refuses_placeholder_jwt_secret():
    import subprocess, sys
    code = "import app.auth_utils"
    env = {**os.environ, "APP_ENV": "production", "JWT_SECRET_KEY": "change-me-in-production-use-openssl-rand-hex-32"}
    r = subprocess.run([sys.executable, "-c", code], cwd=os.path.join(REPO_ROOT, "backend"), env=env,
                       capture_output=True, text=True)
    assert r.returncode != 0 and "JWT_SECRET_KEY" in r.stderr


def test_production_accepts_strong_jwt_secret():
    import subprocess, sys
    env = {**os.environ, "APP_ENV": "production", "JWT_SECRET_KEY": "a" * 16 + "7f3c9d1b" * 4}
    r = subprocess.run([sys.executable, "-c", "import app.auth_utils"], cwd=os.path.join(REPO_ROOT, "backend"),
                       env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_env_example_documents_required_variables():
    text = open(os.path.join(REPO_ROOT, ".env.example"), encoding="utf-8").read()
    for var in ("JWT_SECRET_KEY", "MANAGER_REGISTRATION_PIN", "ENCRYPTION_KEY", "APP_ENV", "DATABASE_URL",
                "ALLOWED_ORIGINS", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI",
                "GITHUB_TOKEN", "GOOGLE_APPLICATION_CREDENTIALS"):
        assert var in text, var


# ── Bug report limits ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bug_report_rejects_oversized_text(client: AsyncClient, two_tenants):
    h = two_tenants["emp_h"]
    for payload in (
        {"title": "t", "description": "x" * 2001},
        {"title": "t", "description": "ok", "steps_to_reproduce": "y" * 2001},
        {"title": "t" * 201, "description": "ok"},
    ):
        r = await client.post("/api/bug-report", headers=h, json=payload)
        assert r.status_code == 422


@pytest.mark.asyncio
async def test_bug_report_accepts_max_length_text(client: AsyncClient, two_tenants, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    r = await client.post("/api/bug-report", headers=two_tenants["emp_h"],
                          json={"title": "t", "description": "x" * 2000})
    assert r.status_code == 503  # passes validation, fails only because GitHub is not configured


# ── nginx ─────────────────────────────────────────────────────────────────────

def test_nginx_hardening_directives():
    conf = open(os.path.join(REPO_ROOT, "nginx", "nginx.conf"), encoding="utf-8").read()
    assert "limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=10r/m;" in conf
    assert "client_max_body_size 5M;" in conf
    assert 'add_header X-Content-Type-Options "nosniff" always;' in conf
    assert 'add_header X-Frame-Options "DENY" always;' in conf
    assert 'add_header Referrer-Policy "strict-origin-when-cross-origin" always;' in conf
    for loc in ("location /auth {", "location /api/auth/ {", "location = /api/bug-report {",
                "location = /bug-report {"):
        block = conf[conf.index(loc):]
        assert "limit_req zone=auth_limit" in block[:block.index("proxy_pass")], loc
