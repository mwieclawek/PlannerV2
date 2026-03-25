"""pos_v2_schema

Revision ID: 49ece3121735
Revises: a1b2c3d4e5f6
Create Date: 2026-03-25 02:06:02.922254

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '49ece3121735'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # ── Enum types (PostgreSQL only) ──
    if is_postgres:
        op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tablestatus') THEN CREATE TYPE tablestatus AS ENUM ('FREE', 'OCCUPIED', 'BILL_PRINTED', 'DIRTY'); END IF; END $$;")
        op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus') THEN CREATE TYPE orderstatus AS ENUM ('OPEN', 'SENT', 'PARTIALLY_PAID', 'PAID', 'CANCELLED'); END IF; END $$;")
        op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderitemkdsstatus') THEN CREATE TYPE orderitemkdsstatus AS ENUM ('QUEUED', 'PREPARING', 'READY', 'DELIVERED', 'CANCELLED'); END IF; END $$;")
        op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'paymentmethod') THEN CREATE TYPE paymentmethod AS ENUM ('CASH', 'CARD', 'VOUCHER', 'MOBILE'); END IF; END $$;")

    if is_postgres:
        tablestatus_type = postgresql.ENUM('FREE', 'OCCUPIED', 'BILL_PRINTED', 'DIRTY', name='tablestatus', create_type=False)
        orderstatus_type = postgresql.ENUM('OPEN', 'SENT', 'PARTIALLY_PAID', 'PAID', 'CANCELLED', name='orderstatus', create_type=False)
        orderitemkdsstatus_type = postgresql.ENUM('QUEUED', 'PREPARING', 'READY', 'DELIVERED', 'CANCELLED', name='orderitemkdsstatus', create_type=False)
        paymentmethod_type = postgresql.ENUM('CASH', 'CARD', 'VOUCHER', 'MOBILE', name='paymentmethod', create_type=False)
    else:
        tablestatus_type = sa.Enum('FREE', 'OCCUPIED', 'BILL_PRINTED', 'DIRTY', name='tablestatus')
        orderstatus_type = sa.Enum('OPEN', 'SENT', 'PARTIALLY_PAID', 'PAID', 'CANCELLED', name='orderstatus')
        orderitemkdsstatus_type = sa.Enum('QUEUED', 'PREPARING', 'READY', 'DELIVERED', 'CANCELLED', name='orderitemkdsstatus')
        paymentmethod_type = sa.Enum('CASH', 'CARD', 'VOUCHER', 'MOBILE', name='paymentmethod')

    # ── 1. TableZone ──
    if 'tablezone' not in existing_tables:
        op.create_table('tablezone',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
            sa.PrimaryKeyConstraint('id')
        )

    # ── 2. PosTable ──
    if 'postable' not in existing_tables:
        op.create_table('postable',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('zone_id', sa.Uuid(), nullable=True),
            sa.Column('seats', sa.Integer(), nullable=False, server_default='4'),
            sa.Column('status', tablestatus_type, nullable=False, server_default='FREE'),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
            sa.ForeignKeyConstraint(['zone_id'], ['tablezone.id']),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_postable_name'), 'postable', ['name'], unique=False)

    # ── 3. Category (dynamic menu categories) ──
    if 'category' not in existing_tables:
        op.create_table('category',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('color_hex', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='#607D8B'),
            sa.Column('icon_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
        # Seed default categories from the old enum
        op.execute("INSERT INTO category (name, color_hex, sort_order) VALUES ('Zupy', '#FF7043', 1)")
        op.execute("INSERT INTO category (name, color_hex, sort_order) VALUES ('Dania główne', '#42A5F5', 2)")
        op.execute("INSERT INTO category (name, color_hex, sort_order) VALUES ('Desery', '#AB47BC', 3)")
        op.execute("INSERT INTO category (name, color_hex, sort_order) VALUES ('Napoje', '#66BB6A', 4)")

    # ── 4. MenuItem – add new columns ──
    existing_columns = [c['name'] for c in inspector.get_columns('menuitem')]
    if 'description' not in existing_columns:
        op.add_column('menuitem', sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    if 'category_id' not in existing_columns:
        # Map old enum values to new category IDs
        #   SOUPS=1, MAINS=2, DESSERTS=3, DRINKS=4
        op.add_column('menuitem', sa.Column('category_id', sa.Integer(), nullable=True))
        op.execute("UPDATE menuitem SET category_id = CASE category WHEN 'SOUPS' THEN 1 WHEN 'MAINS' THEN 2 WHEN 'DESSERTS' THEN 3 WHEN 'DRINKS' THEN 4 ELSE 2 END")
        
        with op.batch_alter_table('menuitem', schema=None) as batch_op:
            batch_op.alter_column('category_id', existing_type=sa.Integer(), nullable=False)
            # The name for foreign key might be tricky in batch mode for SQLite, but batch_op handles recreating it
            batch_op.create_foreign_key('fk_menuitem_category', 'category', ['category_id'], ['id'])
    if 'tax_rate' not in existing_columns:
        op.add_column('menuitem', sa.Column('tax_rate', sa.Float(), nullable=False, server_default='0.23'))
    if 'kitchen_print' not in existing_columns:
        op.add_column('menuitem', sa.Column('kitchen_print', sa.Boolean(), nullable=False, server_default='1'))
    if 'bar_print' not in existing_columns:
        op.add_column('menuitem', sa.Column('bar_print', sa.Boolean(), nullable=False, server_default='0'))
    if 'sort_order' not in existing_columns:
        op.add_column('menuitem', sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'))

    # ── 5. ModifierGroup ──
    if 'modifiergroup' not in existing_tables:
        op.create_table('modifiergroup',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('min_select', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('max_select', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
            sa.PrimaryKeyConstraint('id')
        )

    # ── 6. Modifier ──
    if 'modifier' not in existing_tables:
        op.create_table('modifier',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('group_id', sa.Integer(), nullable=False),
            sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('price_override', sa.Float(), nullable=False, server_default='0'),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
            sa.ForeignKeyConstraint(['group_id'], ['modifiergroup.id']),
            sa.PrimaryKeyConstraint('id')
        )

    # ── 7. MenuItemModifierGroup (M2M) ──
    if 'menuitemmodifiergroup' not in existing_tables:
        op.create_table('menuitemmodifiergroup',
            sa.Column('menu_item_id', sa.Uuid(), nullable=False),
            sa.Column('modifier_group_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['menu_item_id'], ['menuitem.id']),
            sa.ForeignKeyConstraint(['modifier_group_id'], ['modifiergroup.id']),
            sa.PrimaryKeyConstraint('menu_item_id', 'modifier_group_id')
        )

    # ── 8. Order ──
    if 'order' not in existing_tables:
        op.create_table('order',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('table_id', sa.Uuid(), nullable=False),
            sa.Column('waiter_id', sa.Uuid(), nullable=False),
            sa.Column('status', orderstatus_type, nullable=False, server_default='OPEN'),
            sa.Column('guest_count', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('notes', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('discount_pct', sa.Float(), nullable=False, server_default='0'),
            sa.Column('discount_authorized_by', sa.Uuid(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('closed_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['table_id'], ['postable.id']),
            sa.ForeignKeyConstraint(['waiter_id'], ['user.id']),
            sa.ForeignKeyConstraint(['discount_authorized_by'], ['user.id']),
            sa.PrimaryKeyConstraint('id')
        )

    # ── 9. OrderItem ──
    if 'orderitem' not in existing_tables:
        op.create_table('orderitem',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('order_id', sa.Uuid(), nullable=False),
            sa.Column('menu_item_id', sa.Uuid(), nullable=False),
            sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('unit_price_snapshot', sa.Float(), nullable=False),
            sa.Column('item_name_snapshot', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('course', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('notes', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('kds_status', orderitemkdsstatus_type, nullable=False, server_default='QUEUED'),
            sa.Column('sent_to_kitchen_at', sa.DateTime(), nullable=True),
            sa.Column('ready_at', sa.DateTime(), nullable=True),
            sa.Column('split_tag', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.ForeignKeyConstraint(['order_id'], ['order.id']),
            sa.ForeignKeyConstraint(['menu_item_id'], ['menuitem.id']),
            sa.PrimaryKeyConstraint('id')
        )

    # ── 10. OrderItemModifier ──
    if 'orderitemmodifier' not in existing_tables:
        op.create_table('orderitemmodifier',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('order_item_id', sa.Uuid(), nullable=False),
            sa.Column('modifier_id', sa.Integer(), nullable=False),
            sa.Column('modifier_name_snapshot', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('price_snapshot', sa.Float(), nullable=False, server_default='0'),
            sa.ForeignKeyConstraint(['order_item_id'], ['orderitem.id']),
            sa.ForeignKeyConstraint(['modifier_id'], ['modifier.id']),
            sa.PrimaryKeyConstraint('id')
        )

    # ── 11. Payment ──
    if 'payment' not in existing_tables:
        op.create_table('payment',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('order_id', sa.Uuid(), nullable=False),
            sa.Column('method', paymentmethod_type, nullable=False),
            sa.Column('amount', sa.Float(), nullable=False),
            sa.Column('tip_amount', sa.Float(), nullable=False, server_default='0'),
            sa.Column('received_by', sa.Uuid(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['order_id'], ['order.id']),
            sa.ForeignKeyConstraint(['received_by'], ['user.id']),
            sa.PrimaryKeyConstraint('id')
        )


def downgrade() -> None:
    # Drop new tables in reverse dependency order
    op.drop_table('payment')
    op.drop_table('orderitemmodifier')
    op.drop_table('orderitem')
    op.drop_table('order')
    op.drop_table('menuitemmodifiergroup')
    op.drop_table('modifier')
    op.drop_table('modifiergroup')

    # Revert menuitem columns
    op.drop_constraint('fk_menuitem_category', 'menuitem', type_='foreignkey')
    op.drop_column('menuitem', 'sort_order')
    op.drop_column('menuitem', 'bar_print')
    op.drop_column('menuitem', 'kitchen_print')
    op.drop_column('menuitem', 'tax_rate')
    op.drop_column('menuitem', 'category_id')
    op.drop_column('menuitem', 'description')

    op.drop_table('category')
    op.drop_index(op.f('ix_postable_name'), table_name='postable')
    op.drop_table('postable')
    op.drop_table('tablezone')

    # Drop enum types (PostgreSQL only)
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("DROP TYPE IF EXISTS paymentmethod")
        op.execute("DROP TYPE IF EXISTS orderitemkdsstatus")
        op.execute("DROP TYPE IF EXISTS orderstatus")
        op.execute("DROP TYPE IF EXISTS tablestatus")
