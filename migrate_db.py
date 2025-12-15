import sqlite3
import os

db_path = 'production.db'

if not os.path.exists(db_path):
    print("Database not found.")
    exit(0)

try:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    # Add cons_count
    try:
        cur.execute("SELECT cons_count FROM production_reports LIMIT 1")
        print("cons_count exists.")
    except sqlite3.OperationalError:
        print("Adding cons_count...")
        cur.execute("ALTER TABLE production_reports ADD COLUMN cons_count FLOAT DEFAULT 0")

    # Add cons_unit_weight
    try:
        cur.execute("SELECT cons_unit_weight FROM production_reports LIMIT 1")
        print("cons_unit_weight exists.")
    except sqlite3.OperationalError:
        print("Adding cons_unit_weight...")
        cur.execute("ALTER TABLE production_reports ADD COLUMN cons_unit_weight FLOAT DEFAULT 0")

    con.commit()
    con.close()
    print("Migration successful.")

except Exception as e:
    print(f"Migration failed: {e}")
