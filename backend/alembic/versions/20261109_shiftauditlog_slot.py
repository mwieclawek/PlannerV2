"""add schedule_id, shift_def_id, and date to shiftauditlog

Revision ID: 20261109_shiftauditlog_slot
Revises: 20261020_daily_closeout_cfg
Create Date: 2026-11-09 19:08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261109_shiftauditlog_slot'
down_revision: Union[str, None] = '20261020_daily_closeout_cfg'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'shiftauditlog' in tables:
        cols = [c['name'] for c in inspector.get_columns('shiftauditlog')]
        indexes = [idx['name'] for idx in inspector.get_indexes('shiftauditlog')]
        fks = [fk['name'] for fk in inspector.get_foreign_keys('shiftauditlog') if fk.get('name')]

        with op.batch_alter_table('shiftauditlog') as batch_op:
            if 'schedule_id' not in cols:
                batch_op.add_column(sa.Column('schedule_id', sa.Uuid(), nullable=True))
                if 'fk_shiftauditlog_schedule_id' not in fks:
                    batch_op.create_foreign_key(
                        'fk_shiftauditlog_schedule_id',
                        'schedule',
                        ['schedule_id'],
                        ['id'],
                        ondelete='SET NULL',
                    )
            if 'shift_def_id' not in cols:
                batch_op.add_column(sa.Column('shift_def_id', sa.Integer(), nullable=True))
                if 'fk_shiftauditlog_shift_def_id' not in fks:
                    batch_op.create_foreign_key(
                        'fk_shiftauditlog_shift_def_id',
                        'shiftdefinition',
                        ['shift_def_id'],
                        ['id'],
                        ondelete='SET NULL',
                    )
            if 'date' not in cols:
                batch_op.add_column(sa.Column('date', sa.Date(), nullable=True))

        if 'ix_shiftauditlog_schedule_id' not in indexes:
            op.create_index(op.f('ix_shiftauditlog_schedule_id'), 'shiftauditlog', ['schedule_id'], unique=False)
        if 'ix_shiftauditlog_shift_def_id' not in indexes:
            op.create_index(op.f('ix_shiftauditlog_shift_def_id'), 'shiftauditlog', ['shift_def_id'], unique=False)
        if 'ix_shiftauditlog_date' not in indexes:
            op.create_index(op.f('ix_shiftauditlog_date'), 'shiftauditlog', ['date'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'shiftauditlog' in tables:
        cols = [c['name'] for c in inspector.get_columns('shiftauditlog')]
        indexes = [idx['name'] for idx in inspector.get_indexes('shiftauditlog')]
        fks = [fk['name'] for fk in inspector.get_foreign_keys('shiftauditlog') if fk.get('name')]

        if 'ix_shiftauditlog_date' in indexes:
            op.drop_index(op.f('ix_shiftauditlog_date'), table_name='shiftauditlog')
        if 'ix_shiftauditlog_shift_def_id' in indexes:
            op.drop_index(op.f('ix_shiftauditlog_shift_def_id'), table_name='shiftauditlog')
        if 'ix_shiftauditlog_schedule_id' in indexes:
            op.drop_index(op.f('ix_shiftauditlog_schedule_id'), table_name='shiftauditlog')

        with op.batch_alter_table('shiftauditlog') as batch_op:
            if 'fk_shiftauditlog_shift_def_id' in fks:
                batch_op.drop_constraint('fk_shiftauditlog_shift_def_id', type_='foreignkey')
            if 'fk_shiftauditlog_schedule_id' in fks:
                batch_op.drop_constraint('fk_shiftauditlog_schedule_id', type_='foreignkey')
            if 'date' in cols:
                batch_op.drop_column('date')
            if 'shift_def_id' in cols:
                batch_op.drop_column('shift_def_id')
            if 'schedule_id' in cols:
                batch_op.drop_column('schedule_id')
