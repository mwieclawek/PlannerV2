"""Initial schema - create all tables

Revision ID: 001_initial
Revises: 
Create Date: 2026-02-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # JobRole table
    op.create_table(
        'jobrole',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('color_hex', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # User table
    op.create_table(
        'user',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('password_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('full_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('role_system', sa.Enum('MANAGER', 'EMPLOYEE', name='rolesystem'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)
    
    # ShiftDefinition table
    op.create_table(
        'shiftdefinition',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # UserJobRoleLink (many-to-many)
    op.create_table(
        'userjobrolelink',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['jobrole.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('user_id', 'role_id')
    )
    
    # Availability table
    op.create_table(
        'availability',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('shift_def_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('PREFERRED', 'NEUTRAL', 'UNAVAILABLE', 'AVAILABLE', name='availabilitystatus'), nullable=False),
        sa.ForeignKeyConstraint(['shift_def_id'], ['shiftdefinition.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # StaffingRequirement table
    op.create_table(
        'staffingrequirement',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('shift_def_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('min_count', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['jobrole.id']),
        sa.ForeignKeyConstraint(['shift_def_id'], ['shiftdefinition.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Schedule table
    op.create_table(
        'schedule',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('shift_def_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('is_published', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['jobrole.id']),
        sa.ForeignKeyConstraint(['shift_def_id'], ['shiftdefinition.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # RestaurantConfig table
    op.create_table(
        'restaurantconfig',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('opening_hours', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('address', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('restaurantconfig')
    op.drop_table('schedule')
    op.drop_table('staffingrequirement')
    op.drop_table('availability')
    op.drop_table('userjobrolelink')
    op.drop_table('shiftdefinition')
    op.drop_index(op.f('ix_user_email'), table_name='user')
    op.drop_table('user')
    op.drop_table('jobrole')
