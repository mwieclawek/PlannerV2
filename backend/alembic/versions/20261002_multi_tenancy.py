"""add multi-tenancy support using RestaurantConfig

Revision ID: 20261002_multi_tenancy
Revises: 20260725_add_system_settings
Create Date: 2026-10-02

Uses RestaurantConfig as the primary tenant/client entity.
Adds slug, is_active, created_at to restaurantconfig.
Adds tenant_id FK (pointing to restaurantconfig.id) to User, JobRole, ShiftDefinition,
SystemSettings, TableZone, PosTable, Category, MenuItem, ModifierGroup.
Migrates existing data to the default restaurant.
Adjusts User.username uniqueness from global to per-tenant.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20261002_multi_tenancy'
down_revision = '7c8b9a102030'
branch_labels = None
depends_on = None

DEFAULT_TENANT_ID = 1


def upgrade() -> None:
    # 1. Update restaurantconfig table with multi-tenant fields
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == 'sqlite'
    inspector = sa.inspect(conn)
    rc_columns = [c['name'] for c in inspector.get_columns('restaurantconfig')]
    
    if 'slug' not in rc_columns:
        op.add_column('restaurantconfig', sa.Column('slug', sa.String(), nullable=True))
    if 'is_active' not in rc_columns:
        op.add_column('restaurantconfig', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    if 'created_at' not in rc_columns:
        op.add_column('restaurantconfig', sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))

    # Check if a restaurantconfig row exists
    res = conn.execute(sa.text("SELECT id FROM restaurantconfig LIMIT 1")).fetchone()
    if res and res[0] is not None:
        default_id = int(res[0])
        conn.execute(sa.text("UPDATE restaurantconfig SET slug = 'default', is_active = true WHERE slug IS NULL"))
    else:
        conn.execute(
            sa.text("INSERT INTO restaurantconfig (name, slug, is_active, pos_enabled) VALUES ('Default Restaurant', 'default', true, false)")
        )
        res2 = conn.execute(sa.text("SELECT id FROM restaurantconfig WHERE slug = 'default'")).fetchone()
        default_id = int(res2[0]) if res2 and res2[0] is not None else DEFAULT_TENANT_ID
    
    if not is_sqlite:
        op.alter_column('restaurantconfig', 'slug', nullable=False)
    try:
        op.create_index('ix_restaurantconfig_slug', 'restaurantconfig', ['slug'], unique=True)
    except Exception:
        pass

    # 2. Add tenant_id to User table
    u_cols = [c['name'] for c in inspector.get_columns('user')]
    if 'tenant_id' not in u_cols:
        op.add_column('user', sa.Column('tenant_id', sa.Integer(), nullable=True))
        op.execute(f'UPDATE "user" SET tenant_id = {default_id}')
        if not is_sqlite:
            op.alter_column('user', 'tenant_id', nullable=False)
        try:
            op.create_foreign_key('fk_user_restaurant_id', 'user', 'restaurantconfig', ['tenant_id'], ['id'])
        except Exception:
            pass
        try:
            op.create_index('ix_user_tenant_id', 'user', ['tenant_id'])
        except Exception:
            pass
    try:
        op.create_index('ix_user_email', 'user', ['email'])
    except Exception:
        pass

    # Drop old unique constraint on username and create tenant-scoped one
    try:
        op.drop_constraint('uq_user_username', 'user', type_='unique')
    except Exception:
        try:
            op.drop_index('ix_user_username', table_name='user')
        except Exception:
            pass
    try:
        op.create_unique_constraint('uq_user_tenant_username', 'user', ['tenant_id', 'username'])
    except Exception:
        pass

    # 3. Add tenant_id to JobRole
    jr_cols = [c['name'] for c in inspector.get_columns('jobrole')]
    if 'tenant_id' not in jr_cols:
        op.add_column('jobrole', sa.Column('tenant_id', sa.Integer(), nullable=True))
        op.execute(f"UPDATE jobrole SET tenant_id = {default_id}")
        try:
            op.create_foreign_key('fk_jobrole_restaurant_id', 'jobrole', 'restaurantconfig', ['tenant_id'], ['id'])
        except Exception:
            pass
        try:
            op.create_index('ix_jobrole_tenant_id', 'jobrole', ['tenant_id'])
        except Exception:
            pass

    # 4. Add tenant_id to ShiftDefinition
    sd_cols = [c['name'] for c in inspector.get_columns('shiftdefinition')]
    if 'tenant_id' not in sd_cols:
        op.add_column('shiftdefinition', sa.Column('tenant_id', sa.Integer(), nullable=True))
        op.execute(f"UPDATE shiftdefinition SET tenant_id = {default_id}")
        try:
            op.create_foreign_key('fk_shiftdefinition_restaurant_id', 'shiftdefinition', 'restaurantconfig', ['tenant_id'], ['id'])
        except Exception:
            pass
        try:
            op.create_index('ix_shiftdefinition_tenant_id', 'shiftdefinition', ['tenant_id'])
        except Exception:
            pass

    # 5. SystemSettings: add tenant_id
    all_tables = inspector.get_table_names()
    ss_table = 'system_settings' if 'system_settings' in all_tables else ('systemsettings' if 'systemsettings' in all_tables else None)
    if ss_table:
        ss_cols = [c['name'] for c in inspector.get_columns(ss_table)]
        if 'tenant_id' not in ss_cols:
            op.add_column(ss_table, sa.Column('tenant_id', sa.Integer(), nullable=True))
            op.execute(f'UPDATE "{ss_table}" SET tenant_id = {default_id}')
            try:
                op.create_foreign_key(f'fk_{ss_table}_restaurant_id', ss_table, 'restaurantconfig', ['tenant_id'], ['id'])
            except Exception:
                pass
            try:
                op.create_index(f'ix_{ss_table}_tenant_id', ss_table, ['tenant_id'])
            except Exception:
                pass

    # 6. POS and related tables
    for table_name in ['tablezone', 'postable', 'category', 'menuitem', 'modifiergroup', 'order', 'payment', 'restauranttable', 'kitchenorder']:
        if table_name in all_tables:
            cols = [c['name'] for c in inspector.get_columns(table_name)]
            if 'tenant_id' not in cols:
                op.add_column(table_name, sa.Column('tenant_id', sa.Integer(), nullable=True))
                op.execute(f'UPDATE "{table_name}" SET tenant_id = {default_id}')
                try:
                    op.create_foreign_key(f'fk_{table_name}_restaurant_id', table_name, 'restaurantconfig', ['tenant_id'], ['id'])
                except Exception:
                    pass
                try:
                    op.create_index(f'ix_{table_name}_tenant_id', table_name, ['tenant_id'])
                except Exception:
                    pass


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    all_tables = inspector.get_table_names()

    # Remove tenant_id from POS tables
    for table_name in ['modifiergroup', 'menuitem', 'category', 'postable', 'tablezone', 'order', 'payment', 'restauranttable', 'kitchenorder']:
        if table_name in all_tables:
            try:
                op.drop_index(f'ix_{table_name}_tenant_id', table_name=table_name)
            except Exception:
                pass
            try:
                op.drop_constraint(f'fk_{table_name}_restaurant_id', table_name, type_='foreignkey')
            except Exception:
                pass
            try:
                op.drop_column(table_name, 'tenant_id')
            except Exception:
                pass

    # Remove tenant_id from SystemSettings
    for ss_name in ['system_settings', 'systemsettings']:
        if ss_name in all_tables:
            try:
                op.drop_index(f'ix_{ss_name}_tenant_id', table_name=ss_name)
            except Exception:
                pass
            try:
                op.drop_constraint(f'fk_{ss_name}_restaurant_id', ss_name, type_='foreignkey')
            except Exception:
                pass
            try:
                op.drop_column(ss_name, 'tenant_id')
            except Exception:
                pass

    # Remove tenant_id from ShiftDefinition
    try:
        op.drop_index('ix_shiftdefinition_tenant_id', table_name='shiftdefinition')
    except Exception:
        pass
    try:
        op.drop_constraint('fk_shiftdefinition_restaurant_id', 'shiftdefinition', type_='foreignkey')
    except Exception:
        pass
    try:
        op.drop_column('shiftdefinition', 'tenant_id')
    except Exception:
        pass

    # Remove tenant_id from JobRole
    try:
        op.drop_index('ix_jobrole_tenant_id', table_name='jobrole')
    except Exception:
        pass
    try:
        op.drop_constraint('fk_jobrole_restaurant_id', 'jobrole', type_='foreignkey')
    except Exception:
        pass
    try:
        op.drop_column('jobrole', 'tenant_id')
    except Exception:
        pass

    # Restore User
    try:
        op.drop_constraint('uq_user_tenant_username', 'user', type_='unique')
    except Exception:
        pass
    try:
        op.drop_index('ix_user_email', table_name='user')
    except Exception:
        pass
    try:
        op.drop_index('ix_user_tenant_id', table_name='user')
    except Exception:
        pass
    try:
        op.drop_constraint('fk_user_restaurant_id', 'user', type_='foreignkey')
    except Exception:
        pass
    try:
        op.drop_column('user', 'tenant_id')
    except Exception:
        pass
    try:
        op.create_index('ix_user_username', 'user', ['username'], unique=True)
    except Exception:
        pass

    # Revert restaurantconfig
    try:
        op.drop_index('ix_restaurantconfig_slug', table_name='restaurantconfig')
    except Exception:
        pass
    try:
        op.drop_column('restaurantconfig', 'created_at')
    except Exception:
        pass
    try:
        op.drop_column('restaurantconfig', 'is_active')
    except Exception:
        pass
    try:
        op.drop_column('restaurantconfig', 'slug')
    except Exception:
        pass
