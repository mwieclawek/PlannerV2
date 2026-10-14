"""add target_shift_id to shiftgiveaway and create shiftauditlog table

Revision ID: 20261014_audit_swap
Revises: a4b1b3e614f2
Create Date: 2026-10-14 21:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '20261014_audit_swap'
down_revision: Union[str, None] = 'a4b1b3e614f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Ensure target_shift_id in shiftgiveaway
    if 'shiftgiveaway' in tables:
        giveaway_cols = [c['name'] for c in inspector.get_columns('shiftgiveaway')]
        if 'target_shift_id' not in giveaway_cols:
            with op.batch_alter_table('shiftgiveaway') as batch_op:
                batch_op.add_column(sa.Column('target_shift_id', sa.String(), nullable=True))

    # 2. Ensure is_published on schedule has default true for legacy entries
    if 'schedule' in tables:
        schedule_cols = [c['name'] for c in inspector.get_columns('schedule')]
        if 'is_published' not in schedule_cols:
            with op.batch_alter_table('schedule') as batch_op:
                batch_op.add_column(sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.true()))

    # 3. Create shiftauditlog table if not exists
    if 'shiftauditlog' not in tables:
        op.create_table(
            'shiftauditlog',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column('restaurant_id', sa.Integer(), nullable=False),
            sa.Column('shift_id', sa.String(), nullable=False),
            sa.Column('changed_by_user_id', sa.Uuid(), nullable=True),
            sa.Column('action', sa.String(), nullable=False),
            sa.Column('old_value', sa.String(), nullable=True),
            sa.Column('new_value', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['changed_by_user_id'], ['user.id']),
            sa.ForeignKeyConstraint(['restaurant_id'], ['restaurantconfig.id']),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_shiftauditlog_restaurant_id'), 'shiftauditlog', ['restaurant_id'], unique=False)
        op.create_index(op.f('ix_shiftauditlog_shift_id'), 'shiftauditlog', ['shift_id'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'shiftauditlog' in tables:
        op.drop_index(op.f('ix_shiftauditlog_shift_id'), table_name='shiftauditlog')
        op.drop_index(op.f('ix_shiftauditlog_restaurant_id'), table_name='shiftauditlog')
        op.drop_table('shiftauditlog')

    if 'shiftgiveaway' in tables:
        giveaway_cols = [c['name'] for c in inspector.get_columns('shiftgiveaway')]
        if 'target_shift_id' in giveaway_cols:
            with op.batch_alter_table('shiftgiveaway') as batch_op:
                batch_op.drop_column('target_shift_id')
