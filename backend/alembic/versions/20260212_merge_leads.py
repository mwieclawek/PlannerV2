"""merge heads

Revision ID: merge_20260212
Revises: 004_add_attendance, 1c2a74aa2b86
Create Date: 2026-02-12 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'merge_20260212'
down_revision: Union[str, Sequence[str], None] = ('004_add_attendance', '1c2a74aa2b86')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
