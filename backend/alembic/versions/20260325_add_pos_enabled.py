"""add pos_enabled to restaurant config

Revision ID: a1b2c3d4e5f6
Revises: 0fb76fb496a6
Create Date: 2026-03-25
"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = '0fb76fb496a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('restaurantconfig')]
    
    if 'pos_enabled' not in columns:
        op.add_column('restaurantconfig', sa.Column('pos_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('restaurantconfig')]
    
    if 'pos_enabled' in columns:
        op.drop_column('restaurantconfig', 'pos_enabled')
