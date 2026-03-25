import os
import sqlite3

db_path = "../planner.db" # The actual path alembic.ini uses

if os.path.exists(db_path):
    print(f"Removing {db_path}...")
    try:
        os.remove(db_path)
        print("Database removed successfully.")
    except Exception as e:
        print(f"Error removing {db_path}: {e}")
else:
    print("Database does not exist, nothing to remove.")

print("Running alembic upgrade head...")
os.system("cd ..\\backend && alembic upgrade head")

