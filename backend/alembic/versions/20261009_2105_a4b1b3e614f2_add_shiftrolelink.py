"""add ShiftRoleLink

Revision ID: a4b1b3e614f2
Revises: 221c2083d08f
Create Date: 2026-10-09 21:05:30.319460

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a4b1b3e614f2'
down_revision: Union[str, None] = '221c2083d08f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('shiftrolelink',
    sa.Column('shift_def_id', sa.Integer(), nullable=False),
    sa.Column('role_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['role_id'], ['jobrole.id'], ),
    sa.ForeignKeyConstraint(['shift_def_id'], ['shiftdefinition.id'], ),
    sa.PrimaryKeyConstraint('shift_def_id', 'role_id')
    )


def downgrade() -> None:
    op.drop_table('shiftrolelink')
