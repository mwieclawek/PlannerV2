import sqlite3

def add_column():
    conn = sqlite3.connect("planner.db")
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE user ADD COLUMN manager_pin TEXT")
        print("Column 'manager_pin' added successfully.")
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_column()
