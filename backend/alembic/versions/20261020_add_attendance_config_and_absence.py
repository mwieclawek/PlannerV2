"""add attendance config, tip pool toggle, and absence fields

Revision ID: 20261020_att_cfg_abs
Revises: 20261017_wfm_ops_modules
Create Date: 2026-10-20 02:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261020_att_cfg_abs'
down_revision: Union[str, None] = '20261017_wfm_ops_modules'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'restaurantconfig' in tables:
        cfg_cols = [c['name'] for c in inspector.get_columns('restaurantconfig')]
        with op.batch_alter_table('restaurantconfig') as batch_op:
            if 'require_attendance_registration' not in cfg_cols:
                batch_op.add_column(
                    sa.Column('require_attendance_registration', sa.Boolean(), nullable=False, server_default=sa.false())
                )
            if 'attendance_required_from' not in cfg_cols:
                batch_op.add_column(
                    sa.Column('attendance_required_from', sa.Date(), nullable=True)
                )
            if 'enable_tip_pool' not in cfg_cols:
                batch_op.add_column(
                    sa.Column('enable_tip_pool', sa.Boolean(), nullable=False, server_default=sa.true())
                )

    if 'attendance' in tables:
        att_cols = [c['name'] for c in inspector.get_columns('attendance')]
        with op.batch_alter_table('attendance') as batch_op:
            if 'is_absent' not in att_cols:
                batch_op.add_column(
                    sa.Column('is_absent', sa.Boolean(), nullable=False, server_default=sa.false())
                )
            if 'absence_reason' not in att_cols:
                batch_op.add_column(
                    sa.Column('absence_reason', sa.String(), nullable=True)
                )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'attendance' in tables:
        att_cols = [c['name'] for c in inspector.get_columns('attendance')]
        with op.batch_alter_table('attendance') as batch_op:
            if 'absence_reason' in att_cols:
                batch_op.drop_column('absence_reason')
            if 'is_absent' in att_cols:
                batch_op.drop_column('is_absent')

    if 'restaurantconfig' in tables:
        cfg_cols = [c['name'] for c in inspector.get_columns('restaurantconfig')]
        with op.batch_alter_table('restaurantconfig') as batch_op:
            if 'enable_tip_pool' in cfg_cols:
                batch_op.drop_column('enable_tip_pool')
            if 'attendance_required_from' in cfg_cols:
                batch_op.drop_column('attendance_required_from')
            if 'require_attendance_registration' in cfg_cols:
                batch_op.drop_column('require_attendance_registration')
