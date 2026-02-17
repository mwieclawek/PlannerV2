"""merge heads

Revision ID: 5b071609904e
Revises: add_manager_pin_01, add_giveaway_001
Create Date: 2026-02-18 00:11:20.957858

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '5b071609904e'
down_revision: Union[str, None] = ('add_manager_pin_01', 'add_giveaway_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
