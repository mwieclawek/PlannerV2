"""add kds columns and event log

Revision ID: 5c2a2f9f273c
Revises: 49ece3121735
Create Date: 2026-03-25 03:07:41.891593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '5c2a2f9f273c'
down_revision: Union[str, None] = '49ece3121735'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Adding columns without batch mode for add_column ──
    # SQLite officially supports ADD COLUMN via direct ALTER TABLE 
    # Batch mode can cause issues on empty DB creation when copying tables
    op.add_column('menuitem', sa.Column('prep_time_sec', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('orderitem', sa.Column('prep_time_sec_snapshot', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('orderitem', sa.Column('document_version', sa.Integer(), nullable=False, server_default='1'))

    # ── 2. Batch mode strictly for altering existing enum length ──
    with op.batch_alter_table('orderitem', schema=None) as batch_op:
        batch_op.alter_column('kds_status',
               existing_type=sa.VARCHAR(length=9),
               type_=sa.Enum('NEW', 'ACKNOWLEDGED', 'PREPARING', 'READY', 'DELIVERED', 'VOIDED_PENDING_ACK', 'VOIDED', name='orderitemkdsstatus'),
               existing_nullable=False)
               
    # ── 3. Creating KDS Event Log table ──
    op.create_table('kdseventlog',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('order_item_id', sa.Uuid(), nullable=False),
        sa.Column('action_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('actor_id', sa.Uuid(), nullable=True),
        sa.Column('old_state', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('new_state', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('client_timestamp', sa.DateTime(), nullable=False),
        sa.Column('server_timestamp', sa.DateTime(), nullable=False),
        sa.Column('is_undo', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['order_item_id'], ['orderitem.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kdseventlog_order_item_id'), 'kdseventlog', ['order_item_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_kdseventlog_order_item_id'), table_name='kdseventlog')
    op.drop_table('kdseventlog')

    with op.batch_alter_table('orderitem', schema=None) as batch_op:
        batch_op.alter_column('kds_status',
               existing_type=sa.Enum('NEW', 'ACKNOWLEDGED', 'PREPARING', 'READY', 'DELIVERED', 'VOIDED_PENDING_ACK', 'VOIDED', name='orderitemkdsstatus'),
               type_=sa.VARCHAR(length=9),
               existing_nullable=False)
        batch_op.drop_column('document_version')
        batch_op.drop_column('prep_time_sec_snapshot')

    with op.batch_alter_table('menuitem', schema=None) as batch_op:
        batch_op.drop_column('prep_time_sec')
