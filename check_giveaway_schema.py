import sqlite3

def check_giveaway_schema():
    conn = sqlite3.connect("planner.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(shiftgiveaway)")
    columns = cursor.fetchall()
    print("Columns in 'shiftgiveaway' table:")
    for col in columns:
        print(col)
    conn.close()

if __name__ == "__main__":
    check_giveaway_schema()
