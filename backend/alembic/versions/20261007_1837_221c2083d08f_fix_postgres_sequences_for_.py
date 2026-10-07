"""fix postgres sequences for restaurantconfig and systemsettings

Revision ID: 221c2083d08f
Revises: 20261007_add_is_superadmin
Create Date: 2026-10-07 18:37:03.904802

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '221c2083d08f'
down_revision: Union[str, None] = '20261007_add_is_superadmin'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        # Add sequence for restaurantconfig.id if missing
        conn.execute(sa.text('''
            DO \$\$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'restaurantconfig_id_seq') THEN
                    CREATE SEQUENCE restaurantconfig_id_seq OWNED BY restaurantconfig.id;
                    PERFORM setval('restaurantconfig_id_seq', coalesce(max(id), 0) + 1, false) FROM restaurantconfig;
                    ALTER TABLE restaurantconfig ALTER COLUMN id SET DEFAULT nextval('restaurantconfig_id_seq');
                END IF;
            END
            \$\$;
        '''))
        
        # Add sequence for system_settings.id if missing
        conn.execute(sa.text('''
            DO \$\$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'system_settings_id_seq') THEN
                    CREATE SEQUENCE system_settings_id_seq OWNED BY system_settings.id;
                    PERFORM setval('system_settings_id_seq', coalesce(max(id), 0) + 1, false) FROM system_settings;
                    ALTER TABLE system_settings ALTER COLUMN id SET DEFAULT nextval('system_settings_id_seq');
                END IF;
            END
            \$\$;
        '''))


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        conn.execute(sa.text('''
            ALTER TABLE restaurantconfig ALTER COLUMN id DROP DEFAULT;
            DROP SEQUENCE IF EXISTS restaurantconfig_id_seq;
            ALTER TABLE system_settings ALTER COLUMN id DROP DEFAULT;
            DROP SEQUENCE IF EXISTS system_settings_id_seq;
        '''))
