import sqlite3
import os

db_path = "database.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    # Just in case left over from failed alembic
    try:
        conn.execute("DROP TABLE notification")
        conn.commit()
    except:
        pass
    
    # Also we need to recreate leaverequest to apply the NOT NULL constraint cleanly without alembic altering
    try:
        # Create a tiny backup
        conn.execute("CREATE TABLE leaverequest_old AS SELECT * FROM leaverequest")
        conn.execute("DROP TABLE leaverequest")
        conn.commit()
    except:
        pass
    conn.close()
