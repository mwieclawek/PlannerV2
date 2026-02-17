from sqlalchemy import text
from app.database import engine
from sqlalchemy.orm import Session

def drop_table():
    with Session(engine) as session:
        session.execute(text("DROP TABLE IF EXISTS shiftgiveaway"))
        session.commit()
        print("Dropped shiftgiveaway table")

if __name__ == "__main__":
    drop_table()
