"""Health check endpoint with database migration verification."""
import os
from fastapi import APIRouter, Depends
from sqlmodel import Session, text
from ..database import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(session: Session = Depends(get_session)):
    """
    Public health endpoint returning:
    - db_connected: whether the database is reachable
    - migration_current: whether Alembic head matches current revision
    - current_revision / head_revision: for debugging
    """
    result = {
        "status": "ok",
        "db_connected": False,
        "migration_current": False,
        "current_revision": None,
        "head_revision": None,
    }

    # 1. Check DB connectivity
    try:
        session.exec(text("SELECT 1"))
        result["db_connected"] = True
    except Exception:
        result["status"] = "degraded"
        return result

    # 2. Check Alembic migration state
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from alembic.runtime.migration import MigrationContext

        # Determine alembic.ini path
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        ini_path = os.path.join(base_dir, "alembic.ini")

        alembic_cfg = Config(ini_path)
        script = ScriptDirectory.from_config(alembic_cfg)

        # Get head revision(s)
        heads = script.get_heads()
        result["head_revision"] = heads[0] if heads else None

        # Get current revision from DB
        connection = session.connection()
        migration_ctx = MigrationContext.configure(connection)
        current_revs = migration_ctx.get_current_heads()
        result["current_revision"] = current_revs[0] if current_revs else None

        # Compare
        if result["current_revision"] and result["head_revision"]:
            result["migration_current"] = result["current_revision"] == result["head_revision"]
        elif not heads:
            # No migrations defined = current
            result["migration_current"] = True

        if not result["migration_current"]:
            result["status"] = "degraded"

    except Exception as e:
        result["status"] = "degraded"
        result["migration_error"] = str(e)

    return result
