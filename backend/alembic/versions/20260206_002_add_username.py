"""Add username field, make email optional

Revision ID: 002_add_username
Revises: 001_initial
Create Date: 2026-02-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '002_add_username'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add username column
    op.add_column('user', sa.Column('username', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    
    # Copy email values to username for existing users (migration of existing data)
    op.execute("UPDATE user SET username = email WHERE username IS NULL")
    
    # Make username NOT NULL after data migration
    op.alter_column('user', 'username', nullable=False)
    
    # Create unique index on username
    op.create_index(op.f('ix_user_username'), 'user', ['username'], unique=True)
    
    # Make email nullable (optional)
    op.alter_column('user', 'email', nullable=True)
    
    # Drop unique constraint on email (keep the index but not unique)
    op.drop_index(op.f('ix_user_email'), table_name='user')
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=False)


def downgrade() -> None:
    # Restore unique index on email
    op.drop_index(op.f('ix_user_email'), table_name='user')
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)
    
    # Make email NOT NULL again
    op.alter_column('user', 'email', nullable=False)
    
    # Drop username index and column
    op.drop_index(op.f('ix_user_username'), table_name='user')
    op.drop_column('user', 'username')
