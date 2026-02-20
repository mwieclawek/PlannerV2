import sqlite3

def check_tables():
    conn = sqlite3.connect("planner.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"Tables index: {tables}")
    conn.close()

if __name__ == "__main__":
    check_tables()
