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
    print(resp.text); assert resp.status_code == 200, resp.text
    session.refresh(victim)
    assert victim.is_superadmin is False


# ── restaurants ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_restaurants_with_stats(client: AsyncClient, session: Session, superadmin_headers, test_tenant):
    _make_user(session, test_tenant.id, "emp1", role=RoleSystem.EMPLOYEE)
    resp = await client.get("/sysadmin/restaurants", headers=superadmin_headers)
    print(resp.text); assert resp.status_code == 200
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
    print(resp.text); assert resp.status_code == 200
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
    print(resp.text); assert resp.status_code == 200
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


# ── logs endpoints ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sysadmin_logs_security(client: AsyncClient, auth_headers):
    # Unauthenticated -> 401
    resp = await client.get("/sysadmin/logs")
    assert resp.status_code == 401

    # Regular manager -> 403
    resp = await client.get("/sysadmin/logs", headers=auth_headers)
    assert resp.status_code == 403

    resp = await client.delete("/sysadmin/logs", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_sysadmin_logs_filtering_and_retrieval(
    client: AsyncClient, superadmin_headers, test_tenant, tmp_path, monkeypatch
):
    from pathlib import Path
    import app.services.log_service as log_srv

    # Mock log file with sample multi-tenant entries
    test_log_file = tmp_path / "planner.log"
    sample_content = (
        f"2026-10-22 10:00:00,100 [INFO] [tenant:{test_tenant.id}] app.services.auth: User logged in\n"
        f"2026-10-22 10:01:00,200 [WARNING] [tenant:{test_tenant.id}] app.routers.manager: Low inventory detected\n"
        f"2026-10-22 10:02:00,300 [ERROR] [tenant:{test_tenant.id}] app.routers.pos: Payment gateway timeout\n"
        f"  Traceback (most recent call last):\n"
        f"    File 'gateway.py', line 10\n"
        f"  TimeoutError: Connection failed\n"
        f"2026-10-22 10:03:00,400 [INFO] [tenant:999] app.other: Other restaurant log\n"
        f"2026-10-22 10:04:00,500 [INFO] [tenant:-] app.main: System background maintenance\n"
    )
    test_log_file.write_text(sample_content, encoding="utf-8")

    monkeypatch.setattr(log_srv, "LOG_DIR", tmp_path)
    monkeypatch.setattr(log_srv, "LOG_FILE", test_log_file)

    # 1. Fetch all logs
    resp = await client.get("/sysadmin/logs", headers=superadmin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 5

    # 2. Filter by restaurant_id
    resp = await client.get(f"/sysadmin/logs?restaurant_id={test_tenant.id}", headers=superadmin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    for item in data["items"]:
        assert item["tenant_id"] == test_tenant.id
        assert item["restaurant_name"] == test_tenant.name

    # 3. Filter by level
    resp = await client.get(f"/sysadmin/logs?restaurant_id={test_tenant.id}&level=ERROR", headers=superadmin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["level"] == "ERROR"
    assert "TimeoutError" in data["items"][0]["message"]  # Multi-line traceback preserved

    # 4. Search by keyword
    resp = await client.get("/sysadmin/logs?search=inventory", headers=superadmin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["level"] == "WARNING"

    # 5. Clear logs
    resp = await client.delete("/sysadmin/logs", headers=superadmin_headers)
    assert resp.status_code == 200
    assert "wyczyszczony" in resp.json()["message"]


@pytest.mark.asyncio
async def test_structured_domain_logs_and_sql_noise_filtering(
    client: AsyncClient, superadmin_headers, test_tenant, tmp_path, monkeypatch
):
    """
    Verify:
    1. log_event writes structured JSON logs with category, actor_name, event_title, details,
       and only populates traceback when a real Python exception is logged.
    2. Category filtering (?category=SOLVER, ?category=AUTH) works independently of search.
    3. SQLAlchemy SQL noise lines (SELECT ..., [cached since ...], ROLLBACK) are filtered out
       both by SqlNoiseFilter and get_logs.
    """
    import logging
    import app.services.log_service as log_srv

    test_log_file = tmp_path / "planner_structured.log"
    monkeypatch.setattr(log_srv, "LOG_DIR", tmp_path)
    monkeypatch.setattr(log_srv, "LOG_FILE", test_log_file)

    # Set up temporary file handler with TenantLogFilter + SqlNoiseFilter
    test_logger = logging.getLogger("planner.domain")
    handler = logging.FileHandler(test_log_file, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] [tenant:%(tenant_id)s] %(name)s: %(message)s")
    )
    handler.addFilter(log_srv.TenantLogFilter())
    handler.addFilter(log_srv.SqlNoiseFilter())
    test_logger.addHandler(handler)

    try:
        # 1. Log a normal business event (no exception -> traceback must be None)
        log_srv.log_event(
            category="SOLVER",
            event_title="Wygenerowano grafik tygodniowy (2026-11-02 – 2026-11-08)",
            details={"status": "OPTIMAL", "assigned_shifts": 14, "deficits": 0},
            actor={"id": "u-1", "full_name": "Jan Manager", "username": "jan"},
            tenant_id=test_tenant.id,
            tenant_name=test_tenant.name,
            level="INFO",
        )

        # 2. Log an exception event (real exception -> traceback must be populated)
        try:
            raise ValueError("Błąd synchronizacji z Google Calendar API")
        except ValueError as exc:
            log_srv.log_event(
                category="GCAL",
                event_title="Nieudany eksport zmiany do Google Calendar",
                details={"shift_id": "s-100"},
                actor_name="Anna Kelnerka",
                tenant_id=test_tenant.id,
                level="ERROR",
                exc_info=exc,
            )

        # 3. Inject raw SQL noise lines directly into the file to ensure parser also strips them
        handler.flush()
        with open(test_log_file, "a", encoding="utf-8") as f:
            f.write(
                f"2026-11-02 12:00:00,000 [INFO] [tenant:{test_tenant.id}] sqlalchemy.engine.Engine: SELECT user.id FROM user WHERE user.tenant_id = ?\n"
                f"2026-11-02 12:00:00,001 [INFO] [tenant:{test_tenant.id}] sqlalchemy.engine.Engine: [cached since 0.1234s ago] (1,)\n"
                f"2026-11-02 12:00:00,002 [INFO] [tenant:{test_tenant.id}] sqlalchemy.engine.Engine: ROLLBACK\n"
            )

        # Verify SqlNoiseFilter rejects SQL records directly
        sql_record = logging.LogRecord(
            name="sqlalchemy.engine.Engine",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="SELECT * FROM schedule",
            args=(),
            exc_info=None,
        )
        assert log_srv.SqlNoiseFilter().filter(sql_record) is False

        # Fetch all logs via API -> SQL noise must NOT appear, only the 2 domain events
        resp = await client.get("/sysadmin/logs", headers=superadmin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

        by_cat = {item["category"]: item for item in data["items"]}
        assert "SOLVER" in by_cat
        assert "GCAL" in by_cat

        solver_entry = by_cat["SOLVER"]
        assert solver_entry["actor_name"] == "Jan Manager"
        assert solver_entry["event_title"] == "Wygenerowano grafik tygodniowy (2026-11-02 – 2026-11-08)"
        assert solver_entry["details"]["status"] == "OPTIMAL"
        assert solver_entry["traceback"] is None

        gcal_entry = by_cat["GCAL"]
        assert gcal_entry["actor_name"] == "Anna Kelnerka"
        assert gcal_entry["level"] == "ERROR"
        assert gcal_entry["traceback"] is not None
        assert "ValueError: Błąd synchronizacji z Google Calendar API" in gcal_entry["traceback"]

        # Filter by category=SOLVER AND search=OPTIMAL independently
        resp_cat = await client.get(
            "/sysadmin/logs?category=SOLVER&search=OPTIMAL",
            headers=superadmin_headers,
        )
        assert resp_cat.status_code == 200
        cat_data = resp_cat.json()
        assert cat_data["total"] == 1
        assert cat_data["items"][0]["category"] == "SOLVER"
    finally:
        test_logger.removeHandler(handler)
        handler.close()


# ── DB explorer endpoints ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_db_tables_metadata_and_sensitive_flags(
    client: AsyncClient, session: Session, superadmin_headers, test_tenant
):
    _make_user(session, test_tenant.id, "db_emp1", role=RoleSystem.EMPLOYEE)
    resp = await client.get("/sysadmin/db/tables", headers=superadmin_headers)
    assert resp.status_code == 200, resp.text
    tables = resp.json()["tables"]
    table_names = [t["table_name"] for t in tables]
    assert table_names == sorted(table_names)

    by_name = {t["table_name"]: t for t in tables}
    assert "user" in by_name
    assert "schedule" in by_name
    assert "restaurantconfig" in by_name
    assert "announcement" in by_name

    user_tbl = by_name["user"]
    assert user_tbl["has_tenant_id"] is True
    assert user_tbl["row_count"] >= 2  # superadmin + db_emp1
    user_cols = {c["name"]: c for c in user_tbl["columns"]}
    assert user_cols["password_hash"]["is_sensitive"] is True
    assert user_cols["manager_pin"]["is_sensitive"] is True
    assert user_cols["encrypted_google_access_token"]["is_sensitive"] is True
    assert user_cols["encrypted_google_refresh_token"]["is_sensitive"] is True
    assert user_cols["username"]["is_sensitive"] is False
    assert user_cols["id"]["primary_key"] is True

    # Ensure `is_pinned` is NOT mistakenly flagged as sensitive
    ann_cols = {c["name"]: c for c in by_name["announcement"]["columns"]}
    assert ann_cols["is_pinned"]["is_sensitive"] is False

    # `fcm_token` on userdevice must be sensitive
    dev_cols = {c["name"]: c for c in by_name["userdevice"]["columns"]}
    assert dev_cols["fcm_token"]["is_sensitive"] is True

    assert by_name["schedule"]["has_tenant_id"] is False
    assert by_name["shiftauditlog"]["has_tenant_id"] is True


@pytest.mark.asyncio
async def test_db_table_rows_schedule_fk_resolution(
    client: AsyncClient,
    session: Session,
    superadmin_headers,
    test_tenant,
    shift_definition,
    job_role,
):
    from datetime import date
    from app.models import Schedule

    emp = _make_user(session, test_tenant.id, "kelner_fk", role=RoleSystem.EMPLOYEE)
    emp.full_name = "Jan Kelner"
    session.add(emp)
    session.commit()
    session.refresh(emp)

    sched = Schedule(
        date=date(2026, 11, 18),
        shift_def_id=shift_definition.id,
        user_id=emp.id,
        role_id=job_role.id,
        is_published=True,
    )
    session.add(sched)
    session.commit()
    session.refresh(sched)

    # With resolve_fks=true (default)
    resp_resolved = await client.get(
        "/sysadmin/db/tables/schedule/rows?resolve_fks=true",
        headers=superadmin_headers,
    )
    assert resp_resolved.status_code == 200, resp_resolved.text
    body_res = resp_resolved.json()
    assert body_res["table_name"] == "schedule"
    assert body_res["total"] == 1
    row_res = body_res["rows"][0]
    assert row_res["user_id"] == f"{emp.username} ({emp.full_name}) [#{emp.id}]"
    assert row_res["role_id"] == f"{job_role.name} [#{job_role.id}]"
    expected_shift = (
        f"{shift_definition.name} "
        f"({str(shift_definition.start_time)[:5]}-{str(shift_definition.end_time)[:5]}) "
        f"[#{shift_definition.id}]"
    )
    assert row_res["shift_def_id"] == expected_shift

    # With resolve_fks=false
    resp_raw = await client.get(
        "/sysadmin/db/tables/schedule/rows?resolve_fks=false",
        headers=superadmin_headers,
    )
    assert resp_raw.status_code == 200, resp_raw.text
    row_raw = resp_raw.json()["rows"][0]
    assert row_raw["user_id"] == str(emp.id)
    assert row_raw["role_id"] == job_role.id
    assert row_raw["shift_def_id"] == shift_definition.id


@pytest.mark.asyncio
async def test_db_table_rows_user_redaction_filtering_sorting_and_tenant_fk(
    client: AsyncClient, session: Session, superadmin_headers, test_tenant
):
    other_rest = RestaurantConfig(name="Bistro Roma", slug="bistro-roma")
    session.add(other_rest)
    session.commit()
    session.refresh(other_rest)

    u_alpha = _make_user(session, test_tenant.id, "alpha_user", email="alpha@test.pl", role=RoleSystem.EMPLOYEE)
    u_alpha.manager_pin = "9999"
    u_alpha.encrypted_google_access_token = "secret-gcal-token"
    session.add(u_alpha)

    u_zeta = _make_user(session, test_tenant.id, "zeta_user", email="zeta@test.pl", role=RoleSystem.EMPLOYEE)
    _make_user(session, other_rest.id, "roma_user", email="roma@roma.pl", role=RoleSystem.MANAGER)
    session.commit()

    # Filter by tenant_id + sort_by=username ascending + resolve_fks=true
    resp = await client.get(
        f"/sysadmin/db/tables/user/rows?tenant_id={test_tenant.id}&sort_by=username&sort_desc=false&resolve_fks=true",
        headers=superadmin_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["has_tenant_id"] is True
    usernames = [r["username"] for r in data["rows"]]
    assert usernames == sorted(usernames)
    assert "roma_user" not in usernames
    assert "alpha_user" in usernames
    assert "zeta_user" in usernames

    alpha_row = next(r for r in data["rows"] if r["username"] == "alpha_user")
    assert alpha_row["password_hash"] == "[REDACTED]"
    assert alpha_row["manager_pin"] == "[REDACTED]"
    assert alpha_row["encrypted_google_access_token"] == "[REDACTED]"
    assert alpha_row["tenant_id"] == f"{test_tenant.name} [#{test_tenant.id}]"

    # Search filter + sort_desc=true
    resp_search = await client.get(
        "/sysadmin/db/tables/user/rows?search=roma&sort_by=username&sort_desc=true",
        headers=superadmin_headers,
    )
    assert resp_search.status_code == 200, resp_search.text
    search_data = resp_search.json()
    assert search_data["total"] == 1
    assert search_data["rows"][0]["username"] == "roma_user"
    assert search_data["rows"][0]["tenant_id"] == f"Bistro Roma [#{other_rest.id}]"

    # Searching by a sensitive field value must NOT match (sensitive columns excluded from search)
    resp_secret_search = await client.get(
        "/sysadmin/db/tables/user/rows?search=secret-gcal-token",
        headers=superadmin_headers,
    )
    assert resp_secret_search.status_code == 200
    assert resp_secret_search.json()["total"] == 0

    # Pagination (limit & offset)
    resp_page = await client.get(
        f"/sysadmin/db/tables/user/rows?tenant_id={test_tenant.id}&sort_by=username&sort_desc=false&limit=1&offset=1",
        headers=superadmin_headers,
    )
    assert resp_page.status_code == 200
    page_data = resp_page.json()
    assert page_data["limit"] == 1
    assert page_data["offset"] == 1
    assert page_data["total"] == 3  # owner (superadmin), alpha_user, zeta_user
    assert len(page_data["rows"]) == 1
    assert page_data["rows"][0]["username"] == usernames[1]


@pytest.mark.asyncio
async def test_db_explorer_security_and_validation(
    client: AsyncClient, superadmin_headers, auth_headers, employee_headers
):
    # Unauthenticated -> 401
    assert (await client.get("/sysadmin/db/tables")).status_code == 401
    assert (await client.get("/sysadmin/db/tables/user/rows")).status_code == 401

    # Manager and Employee -> 403 Forbidden
    for hdrs in (auth_headers, employee_headers):
        assert (await client.get("/sysadmin/db/tables", headers=hdrs)).status_code == 403
        assert (await client.get("/sysadmin/db/tables/user/rows", headers=hdrs)).status_code == 403

    # Unknown / SQL-injection table name -> 404
    resp_404 = await client.get(
        "/sysadmin/db/tables/users; DROP TABLE user;--/rows",
        headers=superadmin_headers,
    )
    assert resp_404.status_code == 404

    # Unknown sort_by column -> 400
    resp_400 = await client.get(
        "/sysadmin/db/tables/user/rows?sort_by=nonexistent_col",
        headers=superadmin_headers,
    )
    assert resp_400.status_code == 400


