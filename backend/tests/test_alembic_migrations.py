"""Static guards for Alembic migrations (catch deploy-time failures in CI)."""
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_DIR = Path(__file__).resolve().parent.parent
# alembic_version.version_num is VARCHAR(32) on PostgreSQL
MAX_REVISION_LEN = 32


def _script() -> ScriptDirectory:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return ScriptDirectory.from_config(cfg)


def test_revision_ids_fit_alembic_version_column():
    too_long = [
        f"{r.revision} ({len(r.revision)})"
        for r in _script().walk_revisions()
        if len(r.revision) > MAX_REVISION_LEN
    ]
    assert not too_long, (
        f"Revision ids longer than {MAX_REVISION_LEN} chars break "
        f"alembic_version on PostgreSQL: {too_long}"
    )


def test_single_head_and_linear_graph():
    script = _script()
    heads = script.get_heads()
    assert len(heads) == 1, f"Multiple alembic heads: {heads}"
    ids = [r.revision for r in script.walk_revisions()]
    assert len(ids) == len(set(ids)), "Duplicate revision ids"


def test_down_revisions_exist():
    script = _script()
    known = {r.revision for r in script.walk_revisions()}
    for r in script.walk_revisions():
        downs = r.down_revision
        if downs is None:
            continue
        for d in (downs if isinstance(downs, (tuple, list)) else (downs,)):
            assert d in known, f"{r.revision} points to unknown down_revision {d}"
