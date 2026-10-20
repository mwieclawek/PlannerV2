"""add require_checklists to restaurantconfig

Revision ID: 20261020_add_require_checklists
Revises: 20261020_att_cfg_abs
Create Date: 2026-10-20 18:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261020_add_require_checklists'
down_revision: Union[str, None] = '20261020_att_cfg_abs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'restaurantconfig' in tables:
        cfg_cols = [c['name'] for c in inspector.get_columns('restaurantconfig')]
        with op.batch_alter_table('restaurantconfig') as batch_op:
            if 'require_checklists' not in cfg_cols:
                batch_op.add_column(
                    sa.Column('require_checklists', sa.Boolean(), nullable=False, server_default=sa.true())
                )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'restaurantconfig' in tables:
        cfg_cols = [c['name'] for c in inspector.get_columns('restaurantconfig')]
        with op.batch_alter_table('restaurantconfig') as batch_op:
            if 'require_checklists' in cfg_cols:
                batch_op.drop_column('require_checklists')
