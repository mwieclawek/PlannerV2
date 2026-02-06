"""Add applicable_days to shift_definition

Revision ID: 003_add_applicable_days
Revises: 002_add_username
Create Date: 2026-02-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '003_add_applicable_days'
down_revision: Union[str, None] = '002_add_username'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add applicable_days column with default value (all days)
    op.add_column('shiftdefinition', sa.Column(
        'applicable_days', 
        sqlmodel.sql.sqltypes.AutoString(), 
        nullable=False,
        server_default='0,1,2,3,4,5,6'
    ))


def downgrade() -> None:
    op.drop_column('shiftdefinition', 'applicable_days')
