"""add manager_pin

Revision ID: ad456s789012
Revises: 20260217_add_user_is_active
Create Date: 2026-02-17 23:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'add_manager_pin_01'
down_revision: Union[str, None] = 'add_is_active_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user', sa.Column('manager_pin', sqlmodel.sql.sqltypes.AutoString(), nullable=True))


def downgrade() -> None:
    op.drop_column('user', 'manager_pin')
