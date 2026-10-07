"""Tests for the global SuperAdmin (sysadmin) panel."""
import pytest
from httpx import AsyncClient
from sqlmodel import Session, select

from app.auth_utils import create_access_token, get_password_hash
from app.models import RestaurantConfig, RoleSystem, SystemSettings, User


def _make_user(session: Session, tenant_id: int, username: str, *, email=None,
               role=RoleSystem.MANAGER, superadmin=False, password="Secret123") -> User:
    user = User(
        tenant_id=tenant_id,
        username=username,
        email=email,
        password_hash=get_password_hash(password),
        full_name=username.title(),
        role_system=role,
        is_superadmin=superadmin,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _headers(user: User) -> dict:
    token = create_access_token(data={"sub": user.username, "tenant_id": str(user.tenant_id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def superadmin(session: Session, test_tenant) -> User:
    return _make_user(session, test_tenant.id, "owner", email="owner@restoplan.pl", superadmin=True)


@pytest.fixture
def superadmin_headers(superadmin) -> dict:
    return _headers(superadmin)


# ── access control ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_regular_manager_gets_403(client: AsyncClient, auth_headers):
    for method, url in [
        ("get", "/sysadmin/restaurants"),
        ("post", "/sysadmin/restaurants"),
        ("put", "/sysadmin/restaurants/1/status"),
        ("post", "/sysadmin/restaurants/1/managers"),
    ]:
        resp = await getattr(client, method)(url, headers=auth_headers, **({"json": {}} if method != "get" else {}))
        assert resp.status_code == 403, (method, url, resp.text)


@pytest.mark.asyncio
async def test_unauthenticated_gets_401(client: AsyncClient):
    resp = await client.get("/sysadmin/restaurants")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_exposes_is_superadmin(client: AsyncClient, superadmin_headers, auth_headers):
    me = (await client.get("/auth/me", headers=superadmin_headers)).json()
    assert me["is_superadmin"] is True
    me = (await client.get("/auth/me", headers=auth_headers)).json()
    assert me["is_superadmin"] is False


@pytest.mark.asyncio
async def test_manager_cannot_escalate_via_user_update(
    client: AsyncClient, session: Session, auth_headers, test_tenant
):
    """is_superadmin must be ignored by tenant-level user update endpoint."""
    victim = _make_user(session, test_tenant.id, "worker", role=RoleSystem.EMPLOYEE)
    resp = await client.put(
        f"/manager/users/{victim.id}",
        json={"is_superadmin": True, "full_name": "Worker X"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    session.refresh(victim)
    assert victim.is_superadmin is False


# ── restaurants ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_restaurants_with_stats(client: AsyncClient, session: Session, superadmin_headers, test_tenant):
    _make_user(session, test_tenant.id, "emp1", role=RoleSystem.EMPLOYEE)
    resp = await client.get("/sysadmin/restaurants", headers=superadmin_headers)
    assert resp.status_code == 200
    data = {r["slug"]: r for r in resp.json()}
    assert "test" in data
    # superadmin (MANAGER) + emp1
    assert data["test"]["user_count"] == 2
    assert data["test"]["manager_count"] == 1
    assert data["test"]["is_active"] is True


@pytest.mark.asyncio
async def test_create_restaurant_with_login_id_alias(client: AsyncClient, session: Session, superadmin_headers):
    resp = await client.post(
        "/sysadmin/restaurants",
        json={"name": "Bella Italia", "login_id": "Bella-Italia"},
        headers=superadmin_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["slug"] == "bella-italia"
    assert body["user_count"] == 0
    # per-tenant settings created
    assert session.exec(select(SystemSettings).where(SystemSettings.tenant_id == body["id"])).first()


@pytest.mark.asyncio
async def test_create_restaurant_duplicate_slug_409(client: AsyncClient, superadmin_headers):
    resp = await client.post("/sysadmin/restaurants", json={"name": "Dup", "slug": "test"}, headers=superadmin_headers)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_restaurant_invalid_slug_422(client: AsyncClient, superadmin_headers):
    for payload in [{"name": "X Y"}, {"name": "Ok name", "slug": "bad slug!"}, {"name": "Ok name", "slug": "-x"}]:
        resp = await client.post("/sysadmin/restaurants", json=payload, headers=superadmin_headers)
        assert resp.status_code == 422, payload


@pytest.mark.asyncio
async def test_block_restaurant_blocks_login_and_tokens(client: AsyncClient, session: Session, superadmin_headers):
    other = RestaurantConfig(name="Other", slug="other")
    session.add(other)
    session.commit()
    session.refresh(other)
    mgr = _make_user(session, other.id, "boss", email="boss@other.pl")
    mgr_headers = _headers(mgr)

    resp = await client.put(f"/sysadmin/restaurants/{other.id}/status", json={"is_active": False}, headers=superadmin_headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    login = await client.post("/auth/token", data={"username": "boss@other.pl", "password": "Secret123"})
    assert login.status_code == 403
    # already-issued token is rejected too
    assert (await client.get("/auth/me", headers=mgr_headers)).status_code == 403

    # unblock
    await client.put(f"/sysadmin/restaurants/{other.id}/status", json={"is_active": True}, headers=superadmin_headers)
    login = await client.post("/auth/token", data={"username": "boss@other.pl", "password": "Secret123"})
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_superadmin_not_locked_out_by_blocking_own_restaurant(
    client: AsyncClient, superadmin_headers, test_tenant
):
    resp = await client.put(f"/sysadmin/restaurants/{test_tenant.id}/status", json={"is_active": False}, headers=superadmin_headers)
    assert resp.status_code == 200
    assert (await client.get("/sysadmin/restaurants", headers=superadmin_headers)).status_code == 200
    login = await client.post("/auth/token", data={"username": "owner@restoplan.pl", "password": "Secret123"})
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_status_unknown_restaurant_404(client: AsyncClient, superadmin_headers):
    resp = await client.put("/sysadmin/restaurants/99999/status", json={"is_active": False}, headers=superadmin_headers)
    assert resp.status_code == 404


# ── managers ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_first_manager_and_login_by_email(client: AsyncClient, session: Session, superadmin_headers):
    created = await client.post("/sysadmin/restaurants", json={"name": "Nowa", "slug": "nowa"}, headers=superadmin_headers)
    rid = created.json()["id"]

    resp = await client.post(
        f"/sysadmin/restaurants/{rid}/managers",
        json={"email": "Jan.Kowalski@Nowa.pl", "password": "Haslo1234", "first_name": "Jan", "last_name": "Kowalski"},
        headers=superadmin_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["created"] is True
    assert body["email"] == "jan.kowalski@nowa.pl"
    assert body["username"] == "jan.kowalski"
    assert body["role_system"] == "MANAGER"
    assert body["tenant_id"] == rid

    login = await client.post("/auth/token", data={"username": "jan.kowalski@nowa.pl", "password": "Haslo1234"})
    assert login.status_code == 200
    me = (await client.get("/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"})).json()
    assert me["tenant_slug"] == "nowa"
    assert me["role_system"] == "MANAGER"

    listing = {r["id"]: r for r in (await client.get("/sysadmin/restaurants", headers=superadmin_headers)).json()}
    assert listing[rid]["manager_count"] == 1


@pytest.mark.asyncio
async def test_add_manager_promotes_existing_user_in_same_restaurant(
    client: AsyncClient, session: Session, superadmin_headers, test_tenant
):
    emp = _make_user(session, test_tenant.id, "kelner", email="kelner@test.pl", role=RoleSystem.EMPLOYEE)
    resp = await client.post(
        f"/sysadmin/restaurants/{test_tenant.id}/managers",
        json={"email": "KELNER@test.pl", "password": "Different1", "first_name": "A", "last_name": "B"},
        headers=superadmin_headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["created"] is False
    session.refresh(emp)
    assert emp.role_system == RoleSystem.MANAGER
    # password unchanged
    login = await client.post("/auth/token", data={"username": "kelner@test.pl", "password": "Secret123"})
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_add_manager_email_in_other_restaurant_409(
    client: AsyncClient, session: Session, superadmin_headers, test_tenant
):
    _make_user(session, test_tenant.id, "taken", email="taken@x.pl")
    other = (await client.post("/sysadmin/restaurants", json={"name": "Inna", "slug": "inna"}, headers=superadmin_headers)).json()
    resp = await client.post(
        f"/sysadmin/restaurants/{other['id']}/managers",
        json={"email": "taken@x.pl", "password": "Haslo1234", "first_name": "A", "last_name": "B"},
        headers=superadmin_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_add_manager_username_collision_gets_suffix(
    client: AsyncClient, session: Session, superadmin_headers, test_tenant
):
    _make_user(session, test_tenant.id, "anna", role=RoleSystem.EMPLOYEE)  # no email
    resp = await client.post(
        f"/sysadmin/restaurants/{test_tenant.id}/managers",
        json={"email": "anna@test.pl", "password": "Haslo1234", "first_name": "Anna", "last_name": "N"},
        headers=superadmin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["username"] == "anna2"


@pytest.mark.asyncio
async def test_add_manager_validation(client: AsyncClient, superadmin_headers, test_tenant):
    base = {"email": "ok@ok.pl", "password": "Haslo1234", "first_name": "A", "last_name": "B"}
    for override in [{"email": "not-an-email"}, {"password": "weak"}, {"first_name": "  "}]:
        resp = await client.post(
            f"/sysadmin/restaurants/{test_tenant.id}/managers",
            json={**base, **override},
            headers=superadmin_headers,
        )
        assert resp.status_code == 422, override
    resp = await client.post("/sysadmin/restaurants/99999/managers", json=base, headers=superadmin_headers)
    assert resp.status_code == 404
