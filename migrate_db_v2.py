import sqlite3
import os

db_path = 'production.db'

if not os.path.exists(db_path):
    print("Database not found.")
    exit(0)

try:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    # Add inserted_at
    try:
        cur.execute("SELECT inserted_at FROM production_reports LIMIT 1")
        print("inserted_at exists.")
    except sqlite3.OperationalError:
        print("Adding inserted_at...")
        cur.execute("ALTER TABLE production_reports ADD COLUMN inserted_at DATETIME")
        
        # Populate existing with created_at
        print("Populating existing inserted_at from created_at...")
        cur.execute("UPDATE production_reports SET inserted_at = created_at")

    con.commit()
    con.close()
    print("Migration successful.")

except Exception as e:
    print(f"Migration failed: {e}")
