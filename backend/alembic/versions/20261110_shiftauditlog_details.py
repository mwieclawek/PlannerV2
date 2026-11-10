"""add shift_name_snapshot, role_name_snapshot, target_user_name, actor_name, summary to shiftauditlog

Revision ID: 20261110_shiftauditlog_details
Revises: 20261109_shiftauditlog_slot
Create Date: 2026-11-10 03:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261110_shiftauditlog_details'
down_revision: Union[str, None] = '20261109_shiftauditlog_slot'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'shiftauditlog' in tables:
        cols = [c['name'] for c in inspector.get_columns('shiftauditlog')]

        with op.batch_alter_table('shiftauditlog') as batch_op:
            if 'shift_name_snapshot' not in cols:
                batch_op.add_column(sa.Column('shift_name_snapshot', sa.String(), nullable=True))
            if 'role_name_snapshot' not in cols:
                batch_op.add_column(sa.Column('role_name_snapshot', sa.String(), nullable=True))
            if 'target_user_name' not in cols:
                batch_op.add_column(sa.Column('target_user_name', sa.String(), nullable=True))
            if 'actor_name' not in cols:
                batch_op.add_column(sa.Column('actor_name', sa.String(), nullable=True))
            if 'summary' not in cols:
                batch_op.add_column(sa.Column('summary', sa.String(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'shiftauditlog' in tables:
        cols = [c['name'] for c in inspector.get_columns('shiftauditlog')]

        with op.batch_alter_table('shiftauditlog') as batch_op:
            if 'summary' in cols:
                batch_op.drop_column('summary')
            if 'actor_name' in cols:
                batch_op.drop_column('actor_name')
            if 'target_user_name' in cols:
                batch_op.drop_column('target_user_name')
            if 'role_name_snapshot' in cols:
                batch_op.drop_column('role_name_snapshot')
            if 'shift_name_snapshot' in cols:
                batch_op.drop_column('shift_name_snapshot')
