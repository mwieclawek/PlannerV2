from sqlalchemy import text
from app.database import engine
from sqlalchemy.orm import Session

def check_user_table():
    with Session(engine) as session:
        print("--- Table Info: user ---")
        result = session.execute(text("PRAGMA table_info(user)")).fetchall()
        for row in result:
            print(row)

if __name__ == "__main__":
    check_user_table()
