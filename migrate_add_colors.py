import sqlite3
import os

db_path = 'production.db'

if not os.path.exists(db_path):
    print("Database not found.")
    exit(0)

try:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    # helper to check if col exists
    def col_exists(table, col):
        cur.execute(f"PRAGMA table_info({table})")
        cols = [info[1] for info in cur.fetchall()]
        return col in cols

    # ProductionPlanning
    if not col_exists("production_planning", "color"):
        print("Adding color to production_planning...")
        # Default to a generic blue for existing records
        cur.execute("ALTER TABLE production_planning ADD COLUMN color TEXT DEFAULT '#3b82f6'")
    
    # ProductionReports
    if not col_exists("production_reports", "color"):
        print("Adding color to production_reports...")
        cur.execute("ALTER TABLE production_reports ADD COLUMN color TEXT DEFAULT '#3b82f6'")

    con.commit()
    con.close()
    print("Migration successful: Colors added.")

except Exception as e:
    print(f"Migration failed: {e}")
