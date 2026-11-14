"""add worker_job table for background job tracking and stale recovery

Revision ID: 20261114_worker_job_table
Revises: 20261110_shiftauditlog_details
Create Date: 2026-11-14 16:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261114_worker_job_table'
down_revision: Union[str, None] = '20261110_shiftauditlog_details'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'worker_job' not in tables:
        op.create_table(
            'worker_job',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('job_id', sa.String(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=True),
            sa.Column('job_type', sa.String(), nullable=False),
            sa.Column('status', sa.String(), nullable=False),
            sa.Column('payload_json', sa.String(), nullable=True),
            sa.Column('result_summary_json', sa.String(), nullable=True),
            sa.Column('error_message', sa.String(), nullable=True),
            sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('finished_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['restaurantconfig.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_worker_job_job_id', 'worker_job', ['job_id'], unique=True)
        op.create_index('ix_worker_job_tenant_id', 'worker_job', ['tenant_id'], unique=False)
        op.create_index('ix_worker_job_job_type', 'worker_job', ['job_type'], unique=False)
        op.create_index('ix_worker_job_status', 'worker_job', ['status'], unique=False)
        op.create_index('ix_worker_job_started_at', 'worker_job', ['started_at'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'worker_job' in inspector.get_table_names():
        op.drop_table('worker_job')
