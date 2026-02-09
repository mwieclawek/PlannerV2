"""Add attendance table

Revision ID: 004_add_attendance
Revises: 003_add_applicable_days
Create Date: 2026-02-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = '004_add_attendance'
down_revision: Union[str, None] = '003_add_applicable_days'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create attendance table
    op.create_table(
        'attendance',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('check_in', sa.Time(), nullable=False),
        sa.Column('check_out', sa.Time(), nullable=False),
        sa.Column('was_scheduled', sa.Boolean(), default=True, nullable=False),
        sa.Column('status', sa.String(), default='CONFIRMED', nullable=False),
        sa.Column('schedule_id', UUID(as_uuid=True), sa.ForeignKey('schedule.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('attendance')
