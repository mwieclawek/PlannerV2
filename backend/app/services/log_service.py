"""
System logów PlannerV2.

Dwa źródła wpisów prezentowanych w panelu SuperAdmina:

1. **Zdarzenia domenowe** (`logs/events.jsonl`) zapisywane przez :func:`log_event` –
   ustrukturyzowane rekordy JSON (kategoria, aktor, tytuł zdarzenia, szczegóły,
   opcjonalny traceback). To jest podstawowe, czytelne źródło informacji
   „kto, w jakiej restauracji, co zrobił”.
2. **Logi techniczne** (`logs/planner.log`) z modułu `logging` – prezentowane tylko
   wtedy, gdy niosą wartość diagnostyczną (błędy, ostrzeżenia, starsze wpisy
   z tagami `[SWAP]`, `[SOLVER WORKER]` itp.). Szum SQLAlchemy jest odrzucany
   zarówno przy zapisie (filtr na handlerach), jak i przy odczycie.
"""
import json
import logging
import os
import re
import threading
import traceback as tb_module
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session, select
from ..models import RestaurantConfig
from ..schemas import SysAdminLogEntry, SysAdminLogsResponse
from ..tenant_context import get_current_tenant_id

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "planner.log"
EVENTS_FILE_NAME = "events.jsonl"
EVENTS_MAX_BYTES = 10 * 1024 * 1024
EVENTS_LOGGER_NAME = "planner.events"

# ── Kategorie zdarzeń ──────────────────────────────────────────────────────────
CATEGORIES: List[str] = [
    "SOLVER", "DEFICIT", "SCHEDULE", "AVAILABILITY", "SHIFT_SWAP", "LEAVE",
    "ATTENDANCE", "AUTH", "PUSH", "GCAL", "POS", "ANOMALY", "CONFIG", "USER", "SYSTEM",
]
LEVELS: List[str] = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Mapowanie starszych tagów tekstowych na kategorie (kolejność ma znaczenie –
# najbardziej szczegółowe tagi najpierw).
_LEGACY_TAG_CATEGORIES: List[Tuple[str, str]] = [
    ("[SOLVER WORKER DEFICIT", "DEFICIT"),
    ("[SOLVER WORKER", "SOLVER"),
    ("[SOLVER", "SOLVER"),
    ("[SCHEDULE", "SCHEDULE"),
    ("[AVAILABILITY", "AVAILABILITY"),
    ("[SWAP", "SHIFT_SWAP"),
    ("[LEAVE", "LEAVE"),
    ("[ATTENDANCE", "ATTENDANCE"),
    ("[AUTH", "AUTH"),
    ("[PUSH", "PUSH"),
    ("[MOCK PUSH", "PUSH"),
    ("[GCAL", "GCAL"),
    ("[CONFIG", "CONFIG"),
    ("[USER", "USER"),
    ("[POS", "POS"),
]
_LEGACY_TAG_RE = re.compile(r"^\s*(\[[A-Z][A-Z _]*\]\s*)+")

# Loggery generujące szum na poziomie INFO/DEBUG.
NOISY_LOGGERS: List[str] = [
    "sqlalchemy", "sqlalchemy.engine", "sqlalchemy.engine.Engine", "sqlalchemy.pool",
    "sqlalchemy.dialects", "sqlalchemy.orm", "uvicorn.access", "python_multipart",
    "multipart", "asyncio", "httpx", "httpcore", "urllib3", "passlib", "watchfiles",
]

# Regex for parsing standard formatted log line:
# YYYY-MM-DD HH:MM:SS,mmm [LEVEL] [tenant:ID] logger_name: message
LOG_LINE_REGEX = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:,\d+)?)\s+\[([A-Za-z]+)\](?:\s+\[tenant:(?P<tenant>[^\]]+)\])?\s+([^:]+):\s*(.*)$"
)

# Heuristic regex to detect tenant_id in a message when the tag was not present
TENANT_HEURISTIC_REGEX = re.compile(
    r"(?:tenant_id|tenant_id_1|tenant)[\"']?\s*(?:=|:)\s*[\"']?(\d+)",
    re.IGNORECASE,
)

_write_lock = threading.Lock()


# ── Filtry logowania ───────────────────────────────────────────────────────────

class TenantLogFilter(logging.Filter):
    """Logging filter that injects tenant context information into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        tid = get_current_tenant_id()
        if tid is not None:
            record.tenant_str = f"tenant:{tid}"
            record.tenant_id = tid
        else:
            record.tenant_str = "tenant:-"
            record.tenant_id = None
        return True


def _is_sql_noise(logger_name: str, level_no: int) -> bool:
    return (logger_name or "").startswith("sqlalchemy") and level_no < logging.WARNING


class SqlNoiseFilter(logging.Filter):
    """Odrzuca wpisy SQLAlchemy poniżej poziomu WARNING (zapytania SELECT, `[cached since ...]`)."""

    def filter(self, record: logging.LogRecord) -> bool:
        return not _is_sql_noise(record.name, record.levelno)


def configure_noise_levels() -> None:
    """Ustawia poziom WARNING dla gadatliwych bibliotek (SQLAlchemy, uvicorn.access, ...)."""
    for name in NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


# ── Zdarzenia domenowe ─────────────────────────────────────────────────────────

def _events_file() -> Path:
    return Path(LOG_DIR) / EVENTS_FILE_NAME


def _role_label(role: Any) -> str:
    val = getattr(role, "value", role)
    return {"MANAGER": "Manager", "ADMIN": "Admin", "EMPLOYEE": "Pracownik"}.get(str(val), str(val or ""))


def _resolve_actor(actor: Any) -> Tuple[Optional[str], str]:
    """Zwraca (actor_id, actor_name) dla obiektu User, słownika, krotki lub tekstu."""
    if actor is None:
        return None, "System"
    if isinstance(actor, str):
        return None, actor
    if isinstance(actor, dict):
        resolved_name = (
            actor.get("name")
            or actor.get("full_name")
            or actor.get("actor_name")
            or actor.get("username")
            or "System"
        )
        return (str(actor["id"]) if actor.get("id") is not None else None), str(resolved_name)
    if isinstance(actor, tuple) and len(actor) == 2:
        return (str(actor[0]) if actor[0] is not None else None), str(actor[1])
    actor_id = getattr(actor, "id", None)
    name = getattr(actor, "full_name", None) or getattr(actor, "username", None) or str(actor)
    if getattr(actor, "is_superadmin", False):
        label = "SuperAdmin"
    else:
        label = _role_label(getattr(actor, "role_system", None))
    return (str(actor_id) if actor_id is not None else None), (f"{name} ({label})" if label else name)


def _format_details(details: Any) -> str:
    if details is None:
        return ""
    if isinstance(details, dict):
        return " | ".join(f"{k}: {v}" for k, v in details.items())
    return str(details)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    return str(value)


def _format_traceback(exc_info: Any) -> Optional[str]:
    if not exc_info:
        return None
    if isinstance(exc_info, BaseException):
        return "".join(tb_module.format_exception(type(exc_info), exc_info, exc_info.__traceback__)).rstrip()
    if isinstance(exc_info, tuple) and len(exc_info) == 3:
        return "".join(tb_module.format_exception(*exc_info)).rstrip()
    text = tb_module.format_exc()
    return None if text.strip() == "NoneType: None" else text.rstrip()


def _rotate_events_if_needed(path: Path) -> None:
    try:
        if path.exists() and path.stat().st_size > EVENTS_MAX_BYTES:
            backup = path.with_name(path.name + ".1")
            if backup.exists():
                backup.unlink()
            path.rename(backup)
    except OSError:
        pass


def log_event(
    category: str,
    event_title: str,
    details: Any = None,
    level: str = "INFO",
    actor: Any = None,
    tenant_id: Optional[int] = None,
    exc_info: Any = None,
    tenant_name: Optional[str] = None,
    actor_id: Optional[str] = None,
    actor_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Zapisuje ustrukturyzowane zdarzenie biznesowe.

    :param category: jedna z :data:`CATEGORIES` (np. ``"SCHEDULE"``).
    :param event_title: krótki, czytelny po polsku tytuł („Opublikowano grafik”).
    :param details: słownik lub tekst ze szczegółami biznesowymi.
    :param level: ``INFO`` / ``WARNING`` / ``ERROR`` / ``CRITICAL`` / ``DEBUG``.
    :param actor: obiekt ``User``, tekst (np. ``"System / Solver"``) lub ``(id, nazwa)``.
    :param tenant_id: jawnie przekazany tenant; domyślnie z ``tenant_context``.
    :param exc_info: ``True`` / wyjątek / krotka ``sys.exc_info()`` – zapisuje WYŁĄCZNIE prawdziwy traceback.
    :returns: zapisany rekord (przydatne w testach).
    """
    category = (category or "SYSTEM").upper()
    if category not in CATEGORIES:
        category = "SYSTEM"
    level = (level or "INFO").upper()
    if level == "WARN":
        level = "WARNING"
    if level not in LEVELS:
        level = "INFO"
    if tenant_id is None:
        tenant_id = get_current_tenant_id()
    resolved_actor_id, resolved_actor_name = _resolve_actor(actor)
    if actor_id is not None:
        resolved_actor_id = str(actor_id)
    if actor_name is not None:
        resolved_actor_name = str(actor_name)
    traceback_text = _format_traceback(exc_info)

    record: Dict[str, Any] = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3],
        "level": level,
        "category": category,
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "actor_id": resolved_actor_id,
        "actor_name": resolved_actor_name,
        "event_title": event_title,
        "details": _json_safe(details),
        "traceback": traceback_text,
    }

    try:
        path = _events_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        with _write_lock:
            _rotate_events_if_needed(path)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:  # logowanie nigdy nie może przerwać operacji biznesowej
        pass

    # Lustrzany wpis do standardowego loggera (stdout / docker logs / caplog w testach).
    details_text = _format_details(details)
    msg = f"[{category}] {event_title}" + (f" | {details_text}" if details_text else "") + f" [aktor: {resolved_actor_name}]"
    logging.getLogger(EVENTS_LOGGER_NAME).log(getattr(logging, level, logging.INFO), msg)
    return record


# ── Odczyt ─────────────────────────────────────────────────────────────────────

def _read_raw_lines(max_files: int = 2) -> List[str]:
    """Read lines from planner.log and recent rotated backups (oldest first)."""
    if not Path(LOG_DIR).exists():
        return []
    files_to_read: List[Path] = []
    for i in range(max_files - 1, 0, -1):
        rotated = Path(LOG_DIR) / f"planner.log.{i}"
        if rotated.exists():
            files_to_read.append(rotated)
    if Path(LOG_FILE).exists():
        files_to_read.append(Path(LOG_FILE))

    lines: List[str] = []
    for file_path in files_to_read:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines.extend(f.readlines())
        except Exception:
            pass
    return lines


def _legacy_category(message: str, logger_name: str) -> str:
    for tag, cat in _LEGACY_TAG_CATEGORIES:
        if tag in message:
            return cat
    if "ANOMALY" in message:
        return "ANOMALY"
    if logger_name.startswith("app.routers.pos") or logger_name.startswith("app.services.pos"):
        return "POS"
    return "SYSTEM"


def _parse_raw_entries(raw_lines: List[str]) -> List[dict]:
    """
    Parse raw log lines into structured entries.

    Linie kontynuacji trafiają do pola ``traceback`` wyłącznie, gdy faktycznie
    zawierają zrzut stosu Pythona; w pozostałych przypadkach są doklejane do treści.
    """
    entries: List[dict] = []
    current: Optional[dict] = None

    def _finish(entry: Optional[dict]) -> None:
        if not entry:
            return
        extra = entry.pop("_extra")
        if extra:
            joined = "\n".join(extra)
            if "Traceback (most recent call last)" in joined:
                entry["traceback"] = joined
            else:
                entry["message"] += "\n" + joined
        entries.append(entry)

    for line in raw_lines:
        line_clean = line.rstrip("\r\n")
        match = LOG_LINE_REGEX.match(line_clean)
        if match:
            _finish(current)
            tenant_raw = match.group("tenant")
            message = match.group(5)
            tenant_id: Optional[int] = None
            if tenant_raw and tenant_raw != "-":
                try:
                    tenant_id = int(tenant_raw)
                except ValueError:
                    tenant_id = None
            if tenant_id is None:
                heur = TENANT_HEURISTIC_REGEX.search(message)
                if heur:
                    try:
                        tenant_id = int(heur.group(1))
                    except ValueError:
                        pass
            current = {
                "timestamp": match.group(1),
                "level": match.group(2).upper(),
                "logger": match.group(4).strip(),
                "message": message,
                "tenant_id": tenant_id,
                "traceback": None,
                "_extra": [],
            }
        elif current is not None:
            current["_extra"].append(line_clean)
        elif line_clean.strip():
            current = {
                "timestamp": "", "level": "INFO", "logger": "system", "message": line_clean,
                "tenant_id": None, "traceback": None, "_extra": [],
            }
    _finish(current)
    return entries


def _legacy_to_structured(item: dict) -> dict:
    message = item["message"]
    tb = item.get("traceback")
    first_line = message.splitlines()[0] if message else ""
    title = _LEGACY_TAG_RE.sub("", first_line).strip() or first_line
    extra_lines = "\n".join(message.splitlines()[1:]).strip() if "\n" in message else None
    full_message = f"{message}\n{tb}" if tb else message
    level = item["level"]
    category = _legacy_category(message, item["logger"])
    return {
        "timestamp": item["timestamp"],
        "level": "WARNING" if level == "WARN" else level,
        "category": category,
        "tenant_id": item["tenant_id"],
        "tenant_name": None,
        "actor_id": None,
        "actor_name": "System",
        "event_title": title,
        "details": extra_lines or None,
        "traceback": tb,
        "logger": item["logger"],
        "message": full_message,
    }


def _read_events() -> List[dict]:
    path = _events_file()
    files = [path.with_name(path.name + ".1"), path]
    records: List[dict] = []
    for p in files:
        if not p.exists():
            continue
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(rec, dict):
                        rec.setdefault("logger", EVENTS_LOGGER_NAME)
                        title = rec.get("event_title") or ""
                        det_str = _format_details(rec.get("details"))
                        rec["message"] = f"{title} | {det_str}" if det_str else title
                        records.append(rec)
        except Exception:
            pass
    return records


def _collect_entries() -> List[dict]:
    structured = _read_events()
    for item in _parse_raw_entries(_read_raw_lines()):
        if item["logger"] == EVENTS_LOGGER_NAME:
            continue  # już obecne w events.jsonl
        lvl_no = getattr(logging, item["level"], logging.INFO)
        if _is_sql_noise(item["logger"], lvl_no):
            continue
        structured.append(_legacy_to_structured(item))
    # sort chronologiczny (stabilny), znaczniki czasu mają wspólny format
    structured.sort(key=lambda e: e.get("timestamp") or "")
    return structured


def _details_text(details: Any) -> str:
    if details is None:
        return ""
    if isinstance(details, (dict, list)):
        return json.dumps(details, ensure_ascii=False)
    return str(details)


def get_logs(
    session: Session,
    restaurant_id: Optional[int] = None,
    level: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
    category: Optional[str] = None,
) -> SysAdminLogsResponse:
    """Retrieve and filter log entries for the SuperAdmin panel (newest first)."""
    restaurants = session.exec(select(RestaurantConfig)).all()
    restaurant_map: Dict[int, Tuple[str, str]] = {r.id: (r.name, r.slug) for r in restaurants}

    entries = _collect_entries()
    entries.reverse()

    level_filter = level.strip().upper() if level and level.strip().upper() != "ALL" else None
    category_filter = category.strip().upper() if category and category.strip().upper() != "ALL" else None
    search_filter = search.strip().lower() if search and search.strip() else None

    filtered: List[SysAdminLogEntry] = []
    for item in entries:
        item_tenant = item.get("tenant_id")
        if restaurant_id is not None:
            if restaurant_id == 0:
                if item_tenant is not None:
                    continue
            elif item_tenant != restaurant_id:
                continue

        if level_filter and item.get("level") != level_filter:
            continue

        item_category = item.get("category") or "SYSTEM"
        if category_filter:
            if category_filter == "ANOMALY":
                is_anomaly = item_category == "ANOMALY" or "ANOMALY" in (item.get("message") or "") \
                    or item.get("level") in ("ERROR", "CRITICAL")
                if not is_anomaly:
                    continue
            elif item_category != category_filter:
                continue

        if search_filter:
            haystack = " ".join([
                item.get("event_title") or "", item.get("message") or "", _details_text(item.get("details")),
                item.get("actor_name") or "", item.get("logger") or "", item.get("traceback") or "",
                item_category,
            ]).lower()
            if search_filter not in haystack:
                continue

        rest_name: Optional[str] = item.get("tenant_name")
        rest_slug: Optional[str] = None
        if item_tenant is not None and item_tenant in restaurant_map:
            rest_name, rest_slug = restaurant_map[item_tenant]

        details = item.get("details")
        filtered.append(SysAdminLogEntry(
            timestamp=item.get("timestamp") or "",
            level=item.get("level") or "INFO",
            category=item_category,
            logger=item.get("logger") or "",
            message=item.get("message") or "",
            event_title=item.get("event_title") or item.get("message") or "",
            details=details if isinstance(details, (dict, str)) or details is None else _details_text(details),
            traceback=item.get("traceback") or None,
            actor_id=item.get("actor_id"),
            actor_name=item.get("actor_name") or "System",
            tenant_id=item_tenant,
            tenant_name=rest_name,
            restaurant_name=rest_name,
            restaurant_slug=rest_slug,
        ))

    return SysAdminLogsResponse(
        total=len(filtered),
        items=filtered[offset: offset + limit],
        available_levels=["ALL"] + LEVELS,
        available_categories=["ALL"] + CATEGORIES,
    )


# ── Utrzymanie ─────────────────────────────────────────────────────────────────

def purge_noise_from_logs() -> int:
    """
    Usuwa z `planner.log` (i kopii rotowanych) historyczny szum SQLAlchemy poniżej WARNING.
    Wywoływane przy starcie aplikacji. Zwraca liczbę usuniętych wpisów.
    """
    removed = 0
    if not Path(LOG_DIR).exists():
        return 0
    candidates = [Path(LOG_FILE)] + [Path(LOG_DIR) / f"planner.log.{i}" for i in range(1, 4)]
    for path in candidates:
        if not path.exists():
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            kept: List[str] = []
            skipping = False
            for line in lines:
                match = LOG_LINE_REGEX.match(line.rstrip("\r\n"))
                if match:
                    lvl_no = getattr(logging, match.group(2).upper(), logging.INFO)
                    skipping = _is_sql_noise(match.group(4).strip(), lvl_no)
                    if skipping:
                        removed += 1
                        continue
                    kept.append(line)
                elif not skipping:
                    kept.append(line)
            if len(kept) != len(lines):
                with open(path, "w", encoding="utf-8") as f:
                    f.writelines(kept)
        except Exception:
            continue
    return removed


def clear_logs() -> bool:
    """Clear planner.log, its rotated copies and the domain events file."""
    try:
        Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("")
        for i in range(1, 4):
            rotated = Path(LOG_DIR) / f"planner.log.{i}"
            if rotated.exists():
                rotated.unlink()
        events = _events_file()
        with _write_lock:
            for p in (events, events.with_name(events.name + ".1")):
                if p.exists():
                    p.unlink()
        return True
    except Exception:
        return False
