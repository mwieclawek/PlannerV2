from sqlalchemy import text
from app.database import engine
from sqlalchemy.orm import Session

def check_table_info():
    with Session(engine) as session:
        # Check table info (columns, types, pk)
        print("--- Table Info: schedule ---")
        result = session.execute(text("PRAGMA table_info(schedule)")).fetchall()
        for row in result:
            print(row)
            
        print("\n--- Index Info: schedule ---")
        result = session.execute(text("PRAGMA index_list(schedule)")).fetchall()
        for row in result:
            print(row)
            
        print("\n--- Foreign Key List: schedule ---")
        result = session.execute(text("PRAGMA foreign_key_list(schedule)")).fetchall()
        for row in result:
            print(row)

if __name__ == "__main__":
    check_table_info()
