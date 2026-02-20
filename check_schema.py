import sqlite3

def check_schema():
    conn = sqlite3.connect("planner.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(user)")
    columns = cursor.fetchall()
    print("Columns in 'user' table:")
    for col in columns:
        print(col)
    conn.close()

if __name__ == "__main__":
    check_schema()
