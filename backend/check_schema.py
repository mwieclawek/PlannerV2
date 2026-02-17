import sqlalchemy
from sqlalchemy import create_engine, inspect
import sys
import os

# Setup path
sys.path.append(os.getcwd())

from app.database import engine

def check_schema():
    inspector = inspect(engine)
    print("Tables:", inspector.get_table_names())
    
    for table in ['schedule', 'user']:
        if table in inspector.get_table_names():
            print(f"\nColumns in {table}:")
            for col in inspector.get_columns(table):
                print(f" - {col['name']} ({col['type']})")
        else:
            print(f"\nTable {table} NOT FOUND")

if __name__ == "__main__":
    check_schema()
