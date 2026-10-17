"""add payroll, checklists, haccp, and announcements tables

Revision ID: 20261017_wfm_ops_modules
Revises: 20261014_audit_swap
Create Date: 2026-10-17 21:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261017_wfm_ops_modules'
down_revision: Union[str, None] = '20261014_audit_swap'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Add hourly_rate to user and jobrole, checklist_skip_reason to attendance
    if 'user' in tables:
        user_cols = [c['name'] for c in inspector.get_columns('user')]
        if 'hourly_rate' not in user_cols:
            with op.batch_alter_table('user') as batch_op:
                batch_op.add_column(sa.Column('hourly_rate', sa.Float(), nullable=True))

    if 'jobrole' in tables:
        role_cols = [c['name'] for c in inspector.get_columns('jobrole')]
        if 'hourly_rate' not in role_cols:
            with op.batch_alter_table('jobrole') as batch_op:
                batch_op.add_column(sa.Column('hourly_rate', sa.Float(), nullable=True))

    if 'attendance' in tables:
        att_cols = [c['name'] for c in inspector.get_columns('attendance')]
        if 'checklist_skip_reason' not in att_cols:
            with op.batch_alter_table('attendance') as batch_op:
                batch_op.add_column(sa.Column('checklist_skip_reason', sa.String(), nullable=True))

    # 2. DailyCloseout table
    if 'dailycloseout' not in tables:
        op.create_table(
            'dailycloseout',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=True),
            sa.Column('date', sa.Date(), nullable=False),
            sa.Column('daily_revenue', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('tip_pool', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('notes', sa.String(), nullable=True),
            sa.Column('created_by', sa.Uuid(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['restaurantconfig.id']),
            sa.ForeignKeyConstraint(['created_by'], ['user.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('tenant_id', 'date', name='uq_dailycloseout_tenant_date'),
        )
        op.create_index(op.f('ix_dailycloseout_tenant_id'), 'dailycloseout', ['tenant_id'], unique=False)
        op.create_index(op.f('ix_dailycloseout_date'), 'dailycloseout', ['date'], unique=False)

    # 3. Checklist tables
    if 'checklisttemplate' not in tables:
        op.create_table(
            'checklisttemplate',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=True),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('description', sa.String(), nullable=True),
            sa.Column('role_id', sa.Integer(), nullable=True),
            sa.Column('shift_period', sa.String(length=50), nullable=False, server_default='OPENING'),
            sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['restaurantconfig.id']),
            sa.ForeignKeyConstraint(['role_id'], ['jobrole.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_checklisttemplate_tenant_id'), 'checklisttemplate', ['tenant_id'], unique=False)
        op.create_index(op.f('ix_checklisttemplate_role_id'), 'checklisttemplate', ['role_id'], unique=False)

    if 'checklisttemplateitem' not in tables:
        op.create_table(
            'checklisttemplateitem',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('template_id', sa.Uuid(), nullable=False),
            sa.Column('title', sa.String(length=300), nullable=False),
            sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.ForeignKeyConstraint(['template_id'], ['checklisttemplate.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_checklisttemplateitem_template_id'), 'checklisttemplateitem', ['template_id'], unique=False)

    if 'checklistcompletion' not in tables:
        op.create_table(
            'checklistcompletion',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=True),
            sa.Column('template_id', sa.Uuid(), nullable=False),
            sa.Column('item_id', sa.Uuid(), nullable=False),
            sa.Column('date', sa.Date(), nullable=False),
            sa.Column('user_id', sa.Uuid(), nullable=False),
            sa.Column('is_completed', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('completed_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['restaurantconfig.id']),
            sa.ForeignKeyConstraint(['template_id'], ['checklisttemplate.id']),
            sa.ForeignKeyConstraint(['item_id'], ['checklisttemplateitem.id']),
            sa.ForeignKeyConstraint(['user_id'], ['user.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_checklistcompletion_tenant_id'), 'checklistcompletion', ['tenant_id'], unique=False)
        op.create_index(op.f('ix_checklistcompletion_template_id'), 'checklistcompletion', ['template_id'], unique=False)
        op.create_index(op.f('ix_checklistcompletion_item_id'), 'checklistcompletion', ['item_id'], unique=False)
        op.create_index(op.f('ix_checklistcompletion_date'), 'checklistcompletion', ['date'], unique=False)
        op.create_index(op.f('ix_checklistcompletion_user_id'), 'checklistcompletion', ['user_id'], unique=False)

    # 4. Digital HACCP tables
    if 'haccpdevice' not in tables:
        op.create_table(
            'haccpdevice',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=True),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('min_temp', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('max_temp', sa.Float(), nullable=False, server_default='4.0'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['restaurantconfig.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_haccpdevice_tenant_id'), 'haccpdevice', ['tenant_id'], unique=False)

    if 'haccplog' not in tables:
        op.create_table(
            'haccplog',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=True),
            sa.Column('log_type', sa.String(length=50), nullable=False, server_default='TEMPERATURE'),
            sa.Column('device_id', sa.Uuid(), nullable=True),
            sa.Column('device_name', sa.String(length=200), nullable=False),
            sa.Column('min_temp', sa.Float(), nullable=True),
            sa.Column('max_temp', sa.Float(), nullable=True),
            sa.Column('measured_temp', sa.Float(), nullable=True),
            sa.Column('is_within_norm', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('corrective_action', sa.String(), nullable=True),
            sa.Column('user_id', sa.Uuid(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['restaurantconfig.id']),
            sa.ForeignKeyConstraint(['device_id'], ['haccpdevice.id']),
            sa.ForeignKeyConstraint(['user_id'], ['user.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_haccplog_tenant_id'), 'haccplog', ['tenant_id'], unique=False)
        op.create_index(op.f('ix_haccplog_device_id'), 'haccplog', ['device_id'], unique=False)
        op.create_index(op.f('ix_haccplog_user_id'), 'haccplog', ['user_id'], unique=False)

    # 5. Announcement & ReadReceipts tables
    if 'announcement' not in tables:
        op.create_table(
            'announcement',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=True),
            sa.Column('author_id', sa.Uuid(), nullable=False),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('content', sa.String(length=5000), nullable=False),
            sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['restaurantconfig.id']),
            sa.ForeignKeyConstraint(['author_id'], ['user.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_announcement_tenant_id'), 'announcement', ['tenant_id'], unique=False)
        op.create_index(op.f('ix_announcement_author_id'), 'announcement', ['author_id'], unique=False)

    if 'announcementreadreceipt' not in tables:
        op.create_table(
            'announcementreadreceipt',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=True),
            sa.Column('announcement_id', sa.Uuid(), nullable=False),
            sa.Column('user_id', sa.Uuid(), nullable=False),
            sa.Column('read_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['restaurantconfig.id']),
            sa.ForeignKeyConstraint(['announcement_id'], ['announcement.id']),
            sa.ForeignKeyConstraint(['user_id'], ['user.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('announcement_id', 'user_id', name='uq_announcement_user_receipt'),
        )
        op.create_index(op.f('ix_announcementreadreceipt_tenant_id'), 'announcementreadreceipt', ['tenant_id'], unique=False)
        op.create_index(op.f('ix_announcementreadreceipt_announcement_id'), 'announcementreadreceipt', ['announcement_id'], unique=False)
        op.create_index(op.f('ix_announcementreadreceipt_user_id'), 'announcementreadreceipt', ['user_id'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    for tbl in [
        'announcementreadreceipt',
        'announcement',
        'haccplog',
        'haccpdevice',
        'checklistcompletion',
        'checklisttemplateitem',
        'checklisttemplate',
        'dailycloseout',
    ]:
        if tbl in tables:
            op.drop_table(tbl)

    if 'attendance' in tables:
        att_cols = [c['name'] for c in inspector.get_columns('attendance')]
        if 'checklist_skip_reason' in att_cols:
            with op.batch_alter_table('attendance') as batch_op:
                batch_op.drop_column('checklist_skip_reason')

    if 'jobrole' in tables:
        role_cols = [c['name'] for c in inspector.get_columns('jobrole')]
        if 'hourly_rate' in role_cols:
            with op.batch_alter_table('jobrole') as batch_op:
                batch_op.drop_column('hourly_rate')

    if 'user' in tables:
        user_cols = [c['name'] for c in inspector.get_columns('user')]
        if 'hourly_rate' in user_cols:
            with op.batch_alter_table('user') as batch_op:
                batch_op.drop_column('hourly_rate')
