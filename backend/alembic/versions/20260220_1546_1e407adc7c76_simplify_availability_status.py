"""simplify_availability_status

Revision ID: 1e407adc7c76
Revises: 5b071609904e
Create Date: 2026-02-20 15:46:54.577594

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '1e407adc7c76'
down_revision: Union[str, None] = '5b071609904e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE availability SET status = 'AVAILABLE' WHERE status IN ('PREFERRED', 'NEUTRAL')")


def downgrade() -> None:
    pass
