import sqlite3

def check_alembic_version():
    conn = sqlite3.connect("planner.db")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT version_num FROM alembic_version")
        versions = cursor.fetchall()
        print(f"Current alembic_versions: {versions}")
    except sqlite3.OperationalError:
        print("alembic_version table does not exist.")
    conn.close()

if __name__ == "__main__":
    check_alembic_version()
