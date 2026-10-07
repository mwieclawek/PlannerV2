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

def index_exists(inspector, table_name, index_name):
    try:
        indexes = inspector.get_indexes(table_name)
        return any(i.get('name') == index_name for i in indexes)
    except Exception:
        return False

def fk_exists(inspector, table_name, fk_name):
    try:
        fks = inspector.get_foreign_keys(table_name)
        return any(fk.get('name') == fk_name for fk in fks)
    except Exception:
        return False

def uq_exists(inspector, table_name, uq_name):
    try:
        uqs = inspector.get_unique_constraints(table_name)
        return any(uq.get('name') == uq_name for uq in uqs)
    except Exception:
        return False

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
        
    if not index_exists(inspector, 'restaurantconfig', 'ix_restaurantconfig_slug'):
        op.create_index('ix_restaurantconfig_slug', 'restaurantconfig', ['slug'], unique=True)

    # 2. Add tenant_id to User table
    u_cols = [c['name'] for c in inspector.get_columns('user')]
    if 'tenant_id' not in u_cols:
        op.add_column('user', sa.Column('tenant_id', sa.Integer(), nullable=True))
        op.execute(f'UPDATE "user" SET tenant_id = {default_id}')
        if not is_sqlite:
            op.alter_column('user', 'tenant_id', nullable=False)
            
    if not fk_exists(inspector, 'user', 'fk_user_restaurant_id') and not is_sqlite:
        op.create_foreign_key('fk_user_restaurant_id', 'user', 'restaurantconfig', ['tenant_id'], ['id'])
        
    if not index_exists(inspector, 'user', 'ix_user_tenant_id'):
        op.create_index('ix_user_tenant_id', 'user', ['tenant_id'])
        
    if not index_exists(inspector, 'user', 'ix_user_email'):
        op.create_index('ix_user_email', 'user', ['email'])

    # Drop old unique constraint on username and create tenant-scoped one
    if uq_exists(inspector, 'user', 'uq_user_username') and not is_sqlite:
        op.drop_constraint('uq_user_username', 'user', type_='unique')
    elif index_exists(inspector, 'user', 'ix_user_username'):
        op.drop_index('ix_user_username', table_name='user')
        
    if not uq_exists(inspector, 'user', 'uq_user_tenant_username') and not is_sqlite:
        op.create_unique_constraint('uq_user_tenant_username', 'user', ['tenant_id', 'username'])

    # 3. Add tenant_id to JobRole
    jr_cols = [c['name'] for c in inspector.get_columns('jobrole')]
    if 'tenant_id' not in jr_cols:
        op.add_column('jobrole', sa.Column('tenant_id', sa.Integer(), nullable=True))
        op.execute(f"UPDATE jobrole SET tenant_id = {default_id}")
        
    if not fk_exists(inspector, 'jobrole', 'fk_jobrole_restaurant_id') and not is_sqlite:
        op.create_foreign_key('fk_jobrole_restaurant_id', 'jobrole', 'restaurantconfig', ['tenant_id'], ['id'])
        
    if not index_exists(inspector, 'jobrole', 'ix_jobrole_tenant_id'):
        op.create_index('ix_jobrole_tenant_id', 'jobrole', ['tenant_id'])

    # 4. Add tenant_id to ShiftDefinition
    sd_cols = [c['name'] for c in inspector.get_columns('shiftdefinition')]
    if 'tenant_id' not in sd_cols:
        op.add_column('shiftdefinition', sa.Column('tenant_id', sa.Integer(), nullable=True))
        op.execute(f"UPDATE shiftdefinition SET tenant_id = {default_id}")
        
    if not fk_exists(inspector, 'shiftdefinition', 'fk_shiftdefinition_restaurant_id') and not is_sqlite:
        op.create_foreign_key('fk_shiftdefinition_restaurant_id', 'shiftdefinition', 'restaurantconfig', ['tenant_id'], ['id'])
        
    if not index_exists(inspector, 'shiftdefinition', 'ix_shiftdefinition_tenant_id'):
        op.create_index('ix_shiftdefinition_tenant_id', 'shiftdefinition', ['tenant_id'])

    # 5. SystemSettings: add tenant_id
    all_tables = inspector.get_table_names()
    ss_table = 'system_settings' if 'system_settings' in all_tables else ('systemsettings' if 'systemsettings' in all_tables else None)
    if ss_table:
        ss_cols = [c['name'] for c in inspector.get_columns(ss_table)]
        if 'tenant_id' not in ss_cols:
            op.add_column(ss_table, sa.Column('tenant_id', sa.Integer(), nullable=True))
            op.execute(f'UPDATE "{ss_table}" SET tenant_id = {default_id}')
            
        if not fk_exists(inspector, ss_table, f'fk_{ss_table}_restaurant_id') and not is_sqlite:
            op.create_foreign_key(f'fk_{ss_table}_restaurant_id', ss_table, 'restaurantconfig', ['tenant_id'], ['id'])
            
        if not index_exists(inspector, ss_table, f'ix_{ss_table}_tenant_id'):
            op.create_index(f'ix_{ss_table}_tenant_id', ss_table, ['tenant_id'])

    # 6. POS and related tables
    for table_name in ['tablezone', 'postable', 'category', 'menuitem', 'modifiergroup', 'order', 'payment', 'restauranttable', 'kitchenorder']:
        if table_name in all_tables:
            cols = [c['name'] for c in inspector.get_columns(table_name)]
            if 'tenant_id' not in cols:
                op.add_column(table_name, sa.Column('tenant_id', sa.Integer(), nullable=True))
                op.execute(f'UPDATE "{table_name}" SET tenant_id = {default_id}')
                
            if not fk_exists(inspector, table_name, f'fk_{table_name}_restaurant_id') and not is_sqlite:
                op.create_foreign_key(f'fk_{table_name}_restaurant_id', table_name, 'restaurantconfig', ['tenant_id'], ['id'])
                
            if not index_exists(inspector, table_name, f'ix_{table_name}_tenant_id'):
                op.create_index(f'ix_{table_name}_tenant_id', table_name, ['tenant_id'])


def downgrade() -> None:
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == 'sqlite'
    inspector = sa.inspect(conn)
    all_tables = inspector.get_table_names()

    # Remove tenant_id from POS tables
    for table_name in ['modifiergroup', 'menuitem', 'category', 'postable', 'tablezone', 'order', 'payment', 'restauranttable', 'kitchenorder']:
        if table_name in all_tables:
            if index_exists(inspector, table_name, f'ix_{table_name}_tenant_id'):
                op.drop_index(f'ix_{table_name}_tenant_id', table_name=table_name)
            if fk_exists(inspector, table_name, f'fk_{table_name}_restaurant_id') and not is_sqlite:
                op.drop_constraint(f'fk_{table_name}_restaurant_id', table_name, type_='foreignkey')
            cols = [c['name'] for c in inspector.get_columns(table_name)]
            if 'tenant_id' in cols and not is_sqlite:
                op.drop_column(table_name, 'tenant_id')

    # Remove tenant_id from SystemSettings
    for ss_name in ['system_settings', 'systemsettings']:
        if ss_name in all_tables:
            if index_exists(inspector, ss_name, f'ix_{ss_name}_tenant_id'):
                op.drop_index(f'ix_{ss_name}_tenant_id', table_name=ss_name)
            if fk_exists(inspector, ss_name, f'fk_{ss_name}_restaurant_id') and not is_sqlite:
                op.drop_constraint(f'fk_{ss_name}_restaurant_id', ss_name, type_='foreignkey')
            cols = [c['name'] for c in inspector.get_columns(ss_name)]
            if 'tenant_id' in cols and not is_sqlite:
                op.drop_column(ss_name, 'tenant_id')

    # Remove tenant_id from ShiftDefinition
    if index_exists(inspector, 'shiftdefinition', 'ix_shiftdefinition_tenant_id'):
        op.drop_index('ix_shiftdefinition_tenant_id', table_name='shiftdefinition')
    if fk_exists(inspector, 'shiftdefinition', 'fk_shiftdefinition_restaurant_id') and not is_sqlite:
        op.drop_constraint('fk_shiftdefinition_restaurant_id', 'shiftdefinition', type_='foreignkey')
    cols = [c['name'] for c in inspector.get_columns('shiftdefinition')]
    if 'tenant_id' in cols and not is_sqlite:
        op.drop_column('shiftdefinition', 'tenant_id')

    # Remove tenant_id from JobRole
    if index_exists(inspector, 'jobrole', 'ix_jobrole_tenant_id'):
        op.drop_index('ix_jobrole_tenant_id', table_name='jobrole')
    if fk_exists(inspector, 'jobrole', 'fk_jobrole_restaurant_id') and not is_sqlite:
        op.drop_constraint('fk_jobrole_restaurant_id', 'jobrole', type_='foreignkey')
    cols = [c['name'] for c in inspector.get_columns('jobrole')]
    if 'tenant_id' in cols and not is_sqlite:
        op.drop_column('jobrole', 'tenant_id')

    # Restore User
    if uq_exists(inspector, 'user', 'uq_user_tenant_username') and not is_sqlite:
        op.drop_constraint('uq_user_tenant_username', 'user', type_='unique')
    if index_exists(inspector, 'user', 'ix_user_email'):
        op.drop_index('ix_user_email', table_name='user')
    if index_exists(inspector, 'user', 'ix_user_tenant_id'):
        op.drop_index('ix_user_tenant_id', table_name='user')
    if fk_exists(inspector, 'user', 'fk_user_restaurant_id') and not is_sqlite:
        op.drop_constraint('fk_user_restaurant_id', 'user', type_='foreignkey')
    cols = [c['name'] for c in inspector.get_columns('user')]
    if 'tenant_id' in cols and not is_sqlite:
        op.drop_column('user', 'tenant_id')
    if not index_exists(inspector, 'user', 'ix_user_username') and not is_sqlite:
        op.create_index('ix_user_username', 'user', ['username'], unique=True)

    # Revert restaurantconfig
    if index_exists(inspector, 'restaurantconfig', 'ix_restaurantconfig_slug'):
        op.drop_index('ix_restaurantconfig_slug', table_name='restaurantconfig')
    cols = [c['name'] for c in inspector.get_columns('restaurantconfig')]
    if not is_sqlite:
        if 'created_at' in cols:
            op.drop_column('restaurantconfig', 'created_at')
        if 'is_active' in cols:
            op.drop_column('restaurantconfig', 'is_active')
        if 'slug' in cols:
            op.drop_column('restaurantconfig', 'slug')
