"""add_shift_giveaway

Revision ID: add_giveaway_001
Revises: add_is_active_001
Create Date: 2026-02-17 01:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'add_giveaway_001'
down_revision: Union[str, None] = 'add_is_active_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'shiftgiveaway',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('schedule_id', sa.Uuid(), nullable=False),
        sa.Column('offered_by', sa.Uuid(), nullable=False),
        sa.Column('status', sa.VARCHAR(), nullable=False, server_default='OPEN'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('taken_by', sa.Uuid(), nullable=True),
        # sa.ForeignKeyConstraint(['schedule_id'], ['schedule.id']),
        # sa.ForeignKeyConstraint(['offered_by'], ['user.id']),
        # sa.ForeignKeyConstraint(['taken_by'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('shiftgiveaway')
