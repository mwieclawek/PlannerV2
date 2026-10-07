"""add is_superadmin flag to user

Revision ID: 20261007_add_is_superadmin
Revises: 20261002_multi_tenancy
Create Date: 2026-10-07

Adds a global (cross-tenant) system-owner flag to the user table.
Existing users get FALSE via server_default. The first superadmin must be
promoted manually with SQL (see README / deployment notes).

NOTE: Written without try/except around DDL on purpose - on PostgreSQL a failed
DDL statement aborts the whole transaction (InFailedSqlTransaction). Existence
is checked with the inspector instead, which keeps the migration idempotent.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20261007_add_is_superadmin'
down_revision = '20261002_multi_tenancy'
branch_labels = None
depends_on = None


def _user_columns() -> list:
    inspector = sa.inspect(op.get_bind())
    return [c['name'] for c in inspector.get_columns('user')]


def upgrade() -> None:
    if 'is_superadmin' not in _user_columns():
        op.add_column(
            'user',
            sa.Column('is_superadmin', sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    if 'is_superadmin' in _user_columns():
        # batch_alter_table makes DROP COLUMN work on SQLite as well
        with op.batch_alter_table('user') as batch_op:
            batch_op.drop_column('is_superadmin')
