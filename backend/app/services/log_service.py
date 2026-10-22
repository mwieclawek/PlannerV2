import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlmodel import Session, select
from ..models import RestaurantConfig
from ..schemas import SysAdminLogEntry, SysAdminLogsResponse
from ..tenant_context import get_current_tenant_id

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "planner.log"

# Regex for parsing standard formatted log line:
# YYYY-MM-DD HH:MM:SS,mmm [LEVEL] [tenant:ID] logger_name: message
# or without tenant:
# YYYY-MM-DD HH:MM:SS,mmm [LEVEL] logger_name: message
LOG_LINE_REGEX = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:,\d+)?)\s+\[([A-Za-z]+)\](?:\s+\[tenant:(?P<tenant>[^\]]+)\])?\s+([^:]+):\s*(.*)$"
)

# Heuristic regex to detect tenant_id in SQL / message when tag was not present
TENANT_HEURISTIC_REGEX = re.compile(
    r"(?:tenant_id|tenant_id_1|tenant)[\"']?\s*(?:=|:)\s*[\"']?(\d+)",
    re.IGNORECASE,
)


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


def _read_raw_lines(max_files: int = 2) -> List[str]:
    """Read lines from current planner.log and recent rotated backup files."""
    if not LOG_DIR.exists():
        return []

    lines: List[str] = []
    # Check current file first
    files_to_read: List[Path] = []
    if LOG_FILE.exists():
        files_to_read.append(LOG_FILE)

    # Rotated backups: planner.log.1, planner.log.2...
    for i in range(1, max_files):
        rotated = LOG_DIR / f"planner.log.{i}"
        if rotated.exists():
            files_to_read.append(rotated)

    # Read from newest to oldest or reverse
    for file_path in files_to_read:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines.extend(f.readlines())
        except Exception:
            pass

    return lines


def _parse_raw_entries(raw_lines: List[str]) -> List[dict]:
    """
    Parse raw log lines into structured log entries.
    Multi-line records (e.g. stack traces) are appended to the preceding log entry.
    """
    entries: List[dict] = []
    current_entry: Optional[dict] = None

    for line in raw_lines:
        line_clean = line.rstrip("\r\n")
        match = LOG_LINE_REGEX.match(line_clean)
        if match:
            # New log entry starts
            if current_entry:
                entries.append(current_entry)

            timestamp = match.group(1)
            level = match.group(2).upper()
            tenant_raw = match.group("tenant")
            logger_name = match.group(4).strip()
            message = match.group(5)

            tenant_id: Optional[int] = None
            if tenant_raw and tenant_raw != "-":
                try:
                    tenant_id = int(tenant_raw)
                except ValueError:
                    tenant_id = None

            # Fallback heuristic if tenant wasn't in the tag
            if tenant_id is None:
                heur_match = TENANT_HEURISTIC_REGEX.search(message)
                if heur_match:
                    try:
                        tenant_id = int(heur_match.group(1))
                    except ValueError:
                        pass

            current_entry = {
                "timestamp": timestamp,
                "level": level,
                "logger": logger_name,
                "message": message,
                "tenant_id": tenant_id,
            }
        else:
            # Continuation of previous message (e.g. traceback, JSON, long line)
            if current_entry:
                current_entry["message"] += "\n" + line_clean
                # Check heuristic on continuation lines too if tenant is still None
                if current_entry["tenant_id"] is None:
                    heur_match = TENANT_HEURISTIC_REGEX.search(line_clean)
                    if heur_match:
                        try:
                            current_entry["tenant_id"] = int(heur_match.group(1))
                        except ValueError:
                            pass
            else:
                # Isolated line at top of file
                current_entry = {
                    "timestamp": "",
                    "level": "INFO",
                    "logger": "system",
                    "message": line_clean,
                    "tenant_id": None,
                }

    if current_entry:
        entries.append(current_entry)

    return entries


def get_logs(
    session: Session,
    restaurant_id: Optional[int] = None,
    level: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> SysAdminLogsResponse:
    """
    Retrieve and filter log entries for the SuperAdmin panel.
    Returns newest logs first.
    """
    # 1. Fetch restaurant name map for enriching tenant_id
    restaurants = session.exec(select(RestaurantConfig)).all()
    restaurant_map: Dict[int, Tuple[str, str]] = {
        r.id: (r.name, r.slug) for r in restaurants
    }

    # 2. Read and parse log lines
    raw_lines = _read_raw_lines()
    parsed_entries = _parse_raw_entries(raw_lines)

    # 3. Sort newest first (reverse chronological order)
    parsed_entries.reverse()

    # 4. Filter entries
    filtered_entries: List[SysAdminLogEntry] = []
    level_filter = level.strip().upper() if level and level.strip().upper() != "ALL" else None
    search_filter = search.strip().lower() if search and search.strip() else None

    for item in parsed_entries:
        item_tenant = item["tenant_id"]

        # Filter by restaurant
        if restaurant_id is not None:
            if restaurant_id == 0:
                # 0 means system / unassigned logs only
                if item_tenant is not None:
                    continue
            else:
                if item_tenant != restaurant_id:
                    continue

        # Filter by log level
        if level_filter:
            if item["level"] != level_filter:
                continue

        # Filter by search phrase
        if search_filter:
            content_to_search = f"{item['logger']} {item['message']}".lower()
            if search_filter not in content_to_search:
                continue

        # Enrich with restaurant metadata
        rest_name: Optional[str] = None
        rest_slug: Optional[str] = None
        if item_tenant is not None and item_tenant in restaurant_map:
            rest_name, rest_slug = restaurant_map[item_tenant]

        filtered_entries.append(
            SysAdminLogEntry(
                timestamp=item["timestamp"],
                level=item["level"],
                logger=item["logger"],
                message=item["message"],
                tenant_id=item_tenant,
                restaurant_name=rest_name,
                restaurant_slug=rest_slug,
            )
        )

    total_count = len(filtered_entries)
    paginated_items = filtered_entries[offset : offset + limit]

    return SysAdminLogsResponse(
        total=total_count,
        items=paginated_items,
        available_levels=["ALL", "INFO", "WARNING", "ERROR", "CRITICAL", "DEBUG"],
    )


def clear_logs() -> bool:
    """Clear the active planner.log file, writing an audit entry."""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("--- Log file cleared by SuperAdmin ---\n")
        return True
    except Exception:
        return False
