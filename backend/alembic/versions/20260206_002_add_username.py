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
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('username', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    
    # Copy email values to username for existing users (migration of existing data)
    op.execute('UPDATE "user" SET username = email WHERE username IS NULL')
    
    # Make username NOT NULL after data migration and create index, make email nullable
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('username', existing_type=sa.VARCHAR(), nullable=False)
        batch_op.create_index(batch_op.f('ix_user_username'), ['username'], unique=True)
        batch_op.alter_column('email', existing_type=sa.VARCHAR(), nullable=True)
        batch_op.drop_index('ix_user_email')
        batch_op.create_index(batch_op.f('ix_user_email'), ['email'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('user', schema=None) as batch_op:
        # Restore unique index on email
        batch_op.drop_index(batch_op.f('ix_user_email'))
        batch_op.create_index(batch_op.f('ix_user_email'), ['email'], unique=True)
        
        # Make email NOT NULL again
        batch_op.alter_column('email', existing_type=sa.VARCHAR(), nullable=False)
        
        # Drop username index and column
        batch_op.drop_index(batch_op.f('ix_user_username'))
        batch_op.drop_column('username')
