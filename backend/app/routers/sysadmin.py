"""
SysAdmin router - global (cross-tenant) panel for the system owner.

Every endpoint here is protected by `get_current_superadmin`, which requires
`User.is_superadmin == True`. These endpoints intentionally do NOT use
`require_tenant`: they operate across all restaurants.
"""
import logging
import re
from datetime import date, datetime, time
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import String, cast, func, or_
from sqlmodel import SQLModel, Session, select

from .. import models as app_models  # noqa: F401 - ensure all tables are registered in SQLModel.metadata
from ..auth_utils import get_current_superadmin, get_password_hash
from ..database import get_session
from ..models import (
    ChecklistTemplate,
    JobRole,
    RestaurantConfig,
    RoleSystem,
    ShiftDefinition,
    SystemSettings,
    User,
)
from ..schemas import (
    SysAdminManagerCreate,
    SysAdminManagerResponse,
    SysAdminRestaurantCreate,
    SysAdminRestaurantResponse,
    SysAdminRestaurantStatusUpdate,
    SysAdminRestaurantUpdate,
    SysAdminUserResponse,
    SysAdminPasswordReset,
    SysAdminLogEntry,
    SysAdminLogsResponse,
)
from ..schemas.tenant import (
    SysAdminDbColumnInfo,
    SysAdminDbTableInfo,
    SysAdminDbTableRowsResponse,
    SysAdminDbTablesResponse,
)
from ..services import log_service

router = APIRouter(
    prefix="/sysadmin",
    tags=["sysadmin"],
    dependencies=[Depends(get_current_superadmin)],
)
logger = logging.getLogger(__name__)


# ── helpers ────────────────────────────────────────────────────────────────────

def _get_restaurant_or_404(session: Session, restaurant_id: int) -> RestaurantConfig:
    restaurant = session.get(RestaurantConfig, restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")
    return restaurant


def _count_by_tenant(session: Session, *extra_filters) -> Dict[int, int]:
    query = (
        select(User.tenant_id, func.count(User.id))
        .where(User.is_active == True, User.tenant_id.is_not(None), *extra_filters)  # noqa: E712
        .group_by(User.tenant_id)
    )
    return {tenant_id: count for tenant_id, count in session.exec(query).all()}


def _to_response(
    restaurant: RestaurantConfig, user_count: int = 0, manager_count: int = 0
) -> SysAdminRestaurantResponse:
    return SysAdminRestaurantResponse(
        id=restaurant.id,
        name=restaurant.name,
        slug=restaurant.slug,
        is_active=restaurant.is_active,
        created_at=restaurant.created_at,
        user_count=user_count,
        manager_count=manager_count,
    )


def _generate_unique_username(session: Session, tenant_id: int, email: str) -> str:
    """Derive a username from the e-mail local part, unique within the restaurant."""
    base = re.sub(r"[^a-z0-9._-]", "", email.split("@", 1)[0].lower())
    if len(base) < 3:
        base = f"{base}manager"
    candidate, suffix = base, 2
    while session.exec(
        select(User.id).where(User.tenant_id == tenant_id, User.username == candidate)
    ).first():
        candidate = f"{base}{suffix}"
        suffix += 1
    return candidate


# ── endpoints ──────────────────────────────────────────────────────────────────

@router.get("/restaurants", response_model=List[SysAdminRestaurantResponse])
def list_restaurants(session: Session = Depends(get_session)):
    """All restaurants with basic stats (active users / managers)."""
    restaurants = session.exec(select(RestaurantConfig).order_by(RestaurantConfig.id)).all()
    user_counts = _count_by_tenant(session)
    manager_counts = _count_by_tenant(session, User.role_system == RoleSystem.MANAGER)
    return [
        _to_response(r, user_counts.get(r.id, 0), manager_counts.get(r.id, 0))
        for r in restaurants
    ]


@router.post(
    "/restaurants",
    response_model=SysAdminRestaurantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_restaurant(
    payload: SysAdminRestaurantCreate,
    session: Session = Depends(get_session),
    superadmin: User = Depends(get_current_superadmin),
):
    existing = session.exec(
        select(RestaurantConfig).where(RestaurantConfig.slug == payload.slug)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Restauracja z identyfikatorem '{payload.slug}' już istnieje",
        )

    restaurant = RestaurantConfig(name=payload.name, slug=payload.slug, is_active=True)
    session.add(restaurant)
    session.flush()  # assigns restaurant.id
    # Per-tenant settings row (kill switch etc.) so the tenant starts fully configured
    session.add(SystemSettings(tenant_id=restaurant.id))
    session.commit()
    session.refresh(restaurant)

    logger.info(
        "SYSADMIN %s created restaurant id=%s slug=%s",
        superadmin.email or superadmin.username, restaurant.id, restaurant.slug,
    )
    log_service.log_event(
        "CONFIG", "Utworzono nową restaurację",
        {"restauracja": restaurant.name, "slug": restaurant.slug},
        actor=superadmin, tenant_id=restaurant.id, tenant_name=restaurant.name,
    )
    return _to_response(restaurant)


@router.put("/restaurants/{restaurant_id}/status", response_model=SysAdminRestaurantResponse)
def update_restaurant_status(
    restaurant_id: int,
    payload: SysAdminRestaurantStatusUpdate,
    session: Session = Depends(get_session),
    superadmin: User = Depends(get_current_superadmin),
):
    """Activate / block a restaurant. Blocked restaurants cannot log in (superadmins exempt)."""
    restaurant = _get_restaurant_or_404(session, restaurant_id)
    restaurant.is_active = payload.is_active
    session.add(restaurant)
    if not payload.is_active:
        # Blocked tenant: its users must stop receiving push notifications
        from ..models import UserDevice
        tenant_user_ids = select(User.id).where(User.tenant_id == restaurant.id)
        for device in session.exec(select(UserDevice).where(UserDevice.user_id.in_(tenant_user_ids))).all():
            session.delete(device)
    session.commit()
    session.refresh(restaurant)

    logger.info(
        "SYSADMIN %s set restaurant id=%s is_active=%s",
        superadmin.email or superadmin.username, restaurant.id, restaurant.is_active,
    )
    log_service.log_event(
        "CONFIG",
        "Odblokowano restaurację" if restaurant.is_active else "Zablokowano restaurację",
        {"restauracja": restaurant.name, "aktywna": restaurant.is_active},
        level="INFO" if restaurant.is_active else "WARNING",
        actor=superadmin, tenant_id=restaurant.id, tenant_name=restaurant.name,
    )
    user_count = _count_by_tenant(session).get(restaurant.id, 0)
    manager_count = _count_by_tenant(
        session, User.role_system == RoleSystem.MANAGER
    ).get(restaurant.id, 0)
    return _to_response(restaurant, user_count, manager_count)


@router.post(
    "/restaurants/{restaurant_id}/managers",
    response_model=SysAdminManagerResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_restaurant_manager(
    restaurant_id: int,
    payload: SysAdminManagerCreate,
    session: Session = Depends(get_session),
    superadmin: User = Depends(get_current_superadmin),
):
    """
    Create a manager account for the restaurant, or promote an existing one.

    E-mail is the global login identifier, so it must be unique across the system.
    The current data model binds a user to exactly ONE restaurant (User.tenant_id),
    therefore an e-mail already used in a *different* restaurant is rejected (409).
    """
    restaurant = _get_restaurant_or_404(session, restaurant_id)

    existing = session.exec(
        select(User).where(func.lower(User.email) == payload.email)
    ).first()

    if existing:
        if existing.tenant_id != restaurant.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Konto z tym adresem e-mail jest już przypisane do innej restauracji",
            )
        # Same restaurant: promote to manager, keep the user's current password.
        existing.role_system = RoleSystem.MANAGER
        existing.is_active = True
        session.add(existing)
        session.commit()
        session.refresh(existing)
        logger.info(
            "SYSADMIN %s promoted user %s to MANAGER in restaurant id=%s",
            superadmin.email or superadmin.username, existing.id, restaurant.id,
        )
        return SysAdminManagerResponse(
            user_id=existing.id,
            email=existing.email,
            username=existing.username,
            full_name=existing.full_name,
            tenant_id=restaurant.id,
            role_system=existing.role_system,
            created=False,
            message="Istniejące konto zostało awansowane na managera (hasło nie zostało zmienione)",
        )

    user = User(
        tenant_id=restaurant.id,
        username=_generate_unique_username(session, restaurant.id, payload.email),
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        full_name=f"{payload.first_name} {payload.last_name}".strip(),
        role_system=RoleSystem.MANAGER,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    logger.info(
        "SYSADMIN %s created MANAGER %s in restaurant id=%s",
        superadmin.email or superadmin.username, user.id, restaurant.id,
    )
    return SysAdminManagerResponse(
        user_id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        tenant_id=restaurant.id,
        role_system=user.role_system,
        created=True,
        message="Utworzono konto managera",
    )

@router.put("/restaurants/{restaurant_id}", response_model=SysAdminRestaurantResponse)
def update_restaurant(
    restaurant_id: int,
    payload: SysAdminRestaurantUpdate,
    session: Session = Depends(get_session),
    superadmin: User = Depends(get_current_superadmin),
):
    """Update a restaurant (name, slug)."""
    restaurant = _get_restaurant_or_404(session, restaurant_id)
    
    new_slug = payload.slug or payload.login_id
    if new_slug:
        existing = session.exec(
            select(RestaurantConfig).where(RestaurantConfig.slug == new_slug, RestaurantConfig.id != restaurant_id)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Restauracja z identyfikatorem '{new_slug}' już istnieje",
            )
        restaurant.slug = new_slug
    
    if payload.name:
        restaurant.name = payload.name
        
    session.add(restaurant)
    session.commit()
    session.refresh(restaurant)

    logger.info(
        "SYSADMIN %s updated restaurant id=%s slug=%s",
        superadmin.email or superadmin.username, restaurant.id, restaurant.slug,
    )
    user_count = _count_by_tenant(session).get(restaurant.id, 0)
    manager_count = _count_by_tenant(
        session, User.role_system == RoleSystem.MANAGER
    ).get(restaurant.id, 0)
    return _to_response(restaurant, user_count, manager_count)

@router.get("/restaurants/{restaurant_id}/users", response_model=List[SysAdminUserResponse])
def get_restaurant_users(
    restaurant_id: int,
    session: Session = Depends(get_session),
    superadmin: User = Depends(get_current_superadmin),
):
    """List all users of a restaurant."""
    _get_restaurant_or_404(session, restaurant_id)
    
    users = session.exec(
        select(User)
        .where(User.tenant_id == restaurant_id)
    ).all()
    
    users.sort(key=lambda u: (0 if u.role_system == RoleSystem.MANAGER else 1, 0 if u.is_active else 1, u.username))
    return users


@router.put("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: UUID,
    payload: SysAdminPasswordReset,
    session: Session = Depends(get_session),
    superadmin: User = Depends(get_current_superadmin),
):
    """Reset any user's password."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    user.password_hash = get_password_hash(payload.new_password)
    session.add(user)
    session.commit()
    
    logger.info(
        "SYSADMIN %s reset password for user %s",
        superadmin.email or superadmin.username, user.id,
    )
    log_service.log_event(
        "AUTH", "Zresetowano hasło użytkownika przez SuperAdmina",
        {"uzytkownik": f"{user.full_name} ({user.username})"},
        level="WARNING", actor=superadmin, tenant_id=user.tenant_id,
    )
    return {"message": "Hasło zostało zmienione"}


@router.get("/logs", response_model=SysAdminLogsResponse)
def get_system_logs(
    restaurant_id: Optional[int] = Query(None, description="Filtruj po ID restauracji (0 = tylko logi systemowe bez tenanta)"),
    level: Optional[str] = Query(None, description="Filtruj po poziomie: ALL, DEBUG, INFO, WARNING, ERROR, CRITICAL"),
    category: Optional[str] = Query(None, description="Filtruj po kategorii: ALL, SOLVER, DEFICIT, SCHEDULE, AVAILABILITY, SHIFT_SWAP, LEAVE, ATTENDANCE, AUTH, PUSH, GCAL, POS, ANOMALY, CONFIG, SYSTEM"),
    search: Optional[str] = Query(None, description="Szukana fraza w logach"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    superadmin: User = Depends(get_current_superadmin),
):
    """
    Pobiera i filtruje logi systemowe dla SuperAdmina.
    Opcjonalnie filtruje po restauracji (restaurant_id), poziomie logowania (level) i kategorii (category).
    """
    return log_service.get_logs(
        session=session,
        restaurant_id=restaurant_id,
        level=level,
        category=category,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.delete("/logs")
def clear_system_logs(
    superadmin: User = Depends(get_current_superadmin),
):
    """Wyczyść aktualny plik logów systemowych."""
    success = log_service.clear_logs()
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Nie udało się wyczyścić pliku logów",
        )
    logger.info(
        "SYSADMIN %s wyczyścił plik logów systemowych",
        superadmin.email or superadmin.username,
    )
    return {"message": "Plik logów został wyczyszczony"}


# ── DB Explorer (read-only) ────────────────────────────────────────────────────

_SENSITIVE_COLUMN_EXACT = frozenset({
    "password_hash",
    "hashed_password",
    "manager_pin",
    "registration_pin",
    "google_access_token",
    "google_refresh_token",
    "fcm_token",
})
_SENSITIVE_COLUMN_SUBSTRINGS = (
    "password",
    "token",
    "secret",
    "manager_pin",
    "registration_pin",
)

_USER_FK_COLUMN_NAMES = frozenset({
    "user_id",
    "employee_id",
    "manager_id",
    "changed_by_user_id",
    "target_user_id",
    "requester_id",
    "offered_by",
    "taken_by",
    "reviewed_by",
    "waiter_id",
    "actor_id",
    "recorded_by_user_id",
    "author_id",
    "created_by",
})
_TENANT_FK_COLUMN_NAMES = frozenset({"tenant_id", "restaurant_id", "config_id"})
_JOB_ROLE_FK_COLUMN_NAMES = frozenset({"role_id"})
_SHIFT_DEF_FK_COLUMN_NAMES = frozenset({"shift_def_id"})
_CHECKLIST_FK_COLUMN_NAMES = frozenset({"checklist_id", "template_id"})
_LEAVE_TYPE_FK_COLUMN_NAMES = frozenset({"leave_type_id"})


def _is_sensitive_column(col_name: str) -> bool:
    lower = col_name.lower()
    if lower in _SENSITIVE_COLUMN_EXACT:
        return True
    return any(sub in lower for sub in _SENSITIVE_COLUMN_SUBSTRINGS)


def _has_tenant_id(table) -> bool:
    return ("tenant_id" in table.c) or ("restaurant_id" in table.c)


def _build_column_infos(table) -> List[SysAdminDbColumnInfo]:
    return [
        SysAdminDbColumnInfo(
            name=col.name,
            type=str(col.type),
            nullable=bool(col.nullable) if col.nullable is not None else True,
            primary_key=bool(col.primary_key),
            foreign_keys=[fk.target_fullname for fk in col.foreign_keys],
            is_sensitive=_is_sensitive_column(col.name),
        )
        for col in table.columns
    ]


def _serialize_db_value(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, UUID):
        return str(val)
    if isinstance(val, (datetime, date, time)):
        return val.isoformat()
    if isinstance(val, Enum):
        return val.value
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    return val


def _coerce_uuid(val: Any) -> Optional[UUID]:
    if val is None:
        return None
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except (ValueError, TypeError):
        return None


def _coerce_int(val: Any) -> Optional[int]:
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val
    try:
        return int(str(val))
    except (ValueError, TypeError):
        return None


def _detect_fk_kind(col) -> Optional[str]:
    """Identify target model category for a column via explicit FK metadata or naming convention."""
    for fk in col.foreign_keys:
        target = fk.target_fullname.lower()
        if target in {"user.id", "users.id"}:
            return "user"
        if target in {"restaurantconfig.id", "tenant.id"}:
            return "tenant"
        if target == "jobrole.id":
            return "job_role"
        if target == "shiftdefinition.id":
            return "shift_def"
        if target == "checklisttemplate.id":
            return "checklist"
        if target == "leavetype.id":
            return "leave_type"

    lower_name = col.name.lower()
    if lower_name in _USER_FK_COLUMN_NAMES:
        return "user"
    if lower_name in _TENANT_FK_COLUMN_NAMES:
        return "tenant"
    if lower_name in _JOB_ROLE_FK_COLUMN_NAMES:
        return "job_role"
    if lower_name in _SHIFT_DEF_FK_COLUMN_NAMES:
        return "shift_def"
    if lower_name in _CHECKLIST_FK_COLUMN_NAMES:
        return "checklist"
    if lower_name in _LEAVE_TYPE_FK_COLUMN_NAMES:
        return "leave_type"
    return None


def _resolve_foreign_keys_in_rows(session: Session, table, rows: List[Dict[str, Any]]) -> None:
    """Batch-resolve foreign key values in `rows` in-place (1 query per target table)."""
    if not rows:
        return

    fk_columns: Dict[str, str] = {}
    for col in table.columns:
        if _is_sensitive_column(col.name):
            continue
        kind = _detect_fk_kind(col)
        if kind:
            fk_columns[col.name] = kind

    if not fk_columns:
        return

    uuid_ids: Dict[str, Set[UUID]] = {"user": set(), "checklist": set()}
    int_ids: Dict[str, Set[int]] = {"tenant": set(), "job_role": set(), "shift_def": set(), "leave_type": set()}

    for row in rows:
        for col_name, kind in fk_columns.items():
            raw_val = row.get(col_name)
            if raw_val is None or raw_val == "":
                continue
            if kind in uuid_ids:
                parsed_uuid = _coerce_uuid(raw_val)
                if parsed_uuid is not None:
                    uuid_ids[kind].add(parsed_uuid)
            elif kind in int_ids:
                parsed_int = _coerce_int(raw_val)
                if parsed_int is not None:
                    int_ids[kind].add(parsed_int)

    uuid_lookups: Dict[str, Dict[str, str]] = {}
    int_lookups: Dict[str, Dict[int, str]] = {}

    if uuid_ids["user"]:
        users = session.exec(select(User).where(User.id.in_(list(uuid_ids["user"])))).all()
        uuid_lookups["user"] = {
            str(u.id): f"{u.username} ({u.full_name}) [#{u.id}]"
            for u in users
        }

    if uuid_ids["checklist"]:
        templates = session.exec(
            select(ChecklistTemplate).where(ChecklistTemplate.id.in_(list(uuid_ids["checklist"])))
        ).all()
        uuid_lookups["checklist"] = {
            str(c.id): f"{c.title} [#{c.id}]"
            for c in templates
        }

    if int_ids["tenant"]:
        restaurants = session.exec(
            select(RestaurantConfig).where(RestaurantConfig.id.in_(list(int_ids["tenant"])))
        ).all()
        int_lookups["tenant"] = {
            int(r.id): f"{r.name} [#{r.id}]"
            for r in restaurants
            if r.id is not None
        }

    if int_ids["job_role"]:
        roles = session.exec(
            select(JobRole).where(JobRole.id.in_(list(int_ids["job_role"])))
        ).all()
        int_lookups["job_role"] = {
            int(role.id): f"{role.name} [#{role.id}]"
            for role in roles
            if role.id is not None
        }

    if int_ids["shift_def"]:
        shift_defs = session.exec(
            select(ShiftDefinition).where(ShiftDefinition.id.in_(list(int_ids["shift_def"])))
        ).all()
        int_lookups["shift_def"] = {
            int(s.id): f"{s.name} ({str(s.start_time)[:5]}-{str(s.end_time)[:5]}) [#{s.id}]"
            for s in shift_defs
            if s.id is not None
        }

    leave_type_model = getattr(app_models, "LeaveType", None)
    if leave_type_model is not None and int_ids["leave_type"]:
        leave_types = session.exec(
            select(leave_type_model).where(leave_type_model.id.in_(list(int_ids["leave_type"])))
        ).all()
        int_lookups["leave_type"] = {
            int(lt.id): f"{getattr(lt, 'name', str(lt.id))} [#{lt.id}]"
            for lt in leave_types
            if getattr(lt, "id", None) is not None
        }

    for row in rows:
        for col_name, kind in fk_columns.items():
            raw_val = row.get(col_name)
            if raw_val is None or raw_val == "":
                continue
            if kind in uuid_lookups:
                parsed_uuid = _coerce_uuid(raw_val)
                lookup_key = str(parsed_uuid) if parsed_uuid is not None else str(raw_val)
                if lookup_key in uuid_lookups[kind]:
                    row[col_name] = uuid_lookups[kind][lookup_key]
            elif kind in int_lookups:
                parsed_int = _coerce_int(raw_val)
                if parsed_int is not None and parsed_int in int_lookups[kind]:
                    row[col_name] = int_lookups[kind][parsed_int]


@router.get("/db/tables", response_model=SysAdminDbTablesResponse)
def list_database_tables(session: Session = Depends(get_session)):
    """List all registered database tables with row counts and column metadata."""
    tables_info: List[SysAdminDbTableInfo] = []
    for table_name, table in sorted(SQLModel.metadata.tables.items(), key=lambda item: item[0]):
        row_count = session.execute(select(func.count()).select_from(table)).scalar() or 0
        tables_info.append(
            SysAdminDbTableInfo(
                table_name=table_name,
                row_count=int(row_count),
                has_tenant_id=_has_tenant_id(table),
                columns=_build_column_infos(table),
            )
        )
    return SysAdminDbTablesResponse(tables=tables_info)


@router.get("/db/tables/{table_name}/rows", response_model=SysAdminDbTableRowsResponse)
def get_database_table_rows(
    table_name: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    tenant_id: Optional[int] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_desc: bool = Query(True),
    resolve_fks: bool = Query(True),
    session: Session = Depends(get_session),
):
    """Browse rows of a whitelisted SQLModel table with filtering, sorting, masking, and FK resolution."""
    table = SQLModel.metadata.tables.get(table_name)
    if table is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tabela '{table_name}' nie istnieje",
        )

    if sort_by is not None and sort_by not in table.c:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Kolumna '{sort_by}' nie istnieje w tabeli '{table_name}'",
        )

    filters = []
    if tenant_id is not None:
        if "tenant_id" in table.c:
            filters.append(table.c.tenant_id == tenant_id)
        elif "restaurant_id" in table.c:
            filters.append(table.c.restaurant_id == tenant_id)
        elif table_name == "restaurantconfig" and "id" in table.c:
            filters.append(table.c.id == tenant_id)

    if search and search.strip():
        term = f"%{search.strip()}%"
        search_clauses = [
            cast(col, String).ilike(term)
            for col in table.columns
            if not _is_sensitive_column(col.name)
        ]
        if search_clauses:
            filters.append(or_(*search_clauses))

    count_stmt = select(func.count()).select_from(table)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = int(session.execute(count_stmt).scalar() or 0)

    if sort_by is not None:
        order_col = table.c[sort_by]
    elif "created_at" in table.c:
        order_col = table.c["created_at"]
    elif "date" in table.c:
        order_col = table.c["date"]
    else:
        pk_cols = list(table.primary_key.columns)
        order_col = pk_cols[0] if pk_cols else list(table.columns)[0]

    order_expr = order_col.desc() if sort_desc else order_col.asc()

    rows_stmt = select(table)
    if filters:
        rows_stmt = rows_stmt.where(*filters)
    rows_stmt = rows_stmt.order_by(order_expr).limit(limit).offset(offset)

    raw_mappings = session.execute(rows_stmt).mappings().all()

    serialized_rows: List[Dict[str, Any]] = []
    for mapping in raw_mappings:
        row_dict: Dict[str, Any] = {}
        for col in table.columns:
            if _is_sensitive_column(col.name):
                row_dict[col.name] = "[REDACTED]"
            else:
                row_dict[col.name] = _serialize_db_value(mapping.get(col.name))
        serialized_rows.append(row_dict)

    if resolve_fks:
        _resolve_foreign_keys_in_rows(session, table, serialized_rows)

    return SysAdminDbTableRowsResponse(
        table_name=table_name,
        total=total,
        limit=limit,
        offset=offset,
        has_tenant_id=_has_tenant_id(table),
        columns=_build_column_infos(table),
        rows=serialized_rows,
    )
