import sys
import traceback
import alembic.config
try:
    alembic.config.main(argv=['upgrade', 'head'])
except Exception as e:
    with open('error_full.txt', 'w', encoding='utf-8') as f:
        f.write(traceback.format_exc())
