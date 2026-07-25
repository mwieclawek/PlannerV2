"""add system_settings table

Revision ID: 7c8b9a102030
Revises: 5c2a2f9f273c
Create Date: 2026-07-25
"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


revision = '7c8b9a102030'
down_revision = '5c2a2f9f273c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    if 'system_settings' not in tables:
        op.create_table(
            'system_settings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('is_login_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('blocked_login_message', sa.String(), nullable=False, server_default="Dostęp do aplikacji został tymczasowo wstrzymany. Skontaktuj się z administratorem."),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Insert default row
        op.execute(
            "INSERT INTO system_settings (id, is_login_enabled, blocked_login_message) "
            "VALUES (1, TRUE, 'Dostęp do aplikacji został tymczasowo wstrzymany. Skontaktuj się z administratorem.')"
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    if 'system_settings' in tables:
        op.drop_table('system_settings')
