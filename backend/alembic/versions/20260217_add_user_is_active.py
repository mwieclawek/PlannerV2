"""add_user_is_active

Revision ID: add_is_active_001
Revises: merge_20260212
Create Date: 2026-02-17 01:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'add_is_active_001'
down_revision: Union[str, None] = 'merge_20260212'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')))


def downgrade() -> None:
    op.drop_column('user', 'is_active')
