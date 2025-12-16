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

    # ProductionReports
    if not col_exists("production_reports", "order_number"):
        print("Adding order_number to production_reports...")
        cur.execute("ALTER TABLE production_reports ADD COLUMN order_number TEXT")
    
    if not col_exists("production_reports", "status"):
        print("Adding status to production_reports...")
        cur.execute("ALTER TABLE production_reports ADD COLUMN status TEXT DEFAULT 'Pending'")
        # Update existing to Pending or Confirmed? Let's say Confirmed for old ones for safety
        cur.execute("UPDATE production_reports SET status = 'Confirmed' WHERE status IS NULL")

    if not col_exists("production_reports", "planning_order_ids"):
        print("Adding planning_order_ids to production_reports...")
        cur.execute("ALTER TABLE production_reports ADD COLUMN planning_order_ids TEXT")

    # ProductionPlanning
    if not col_exists("production_planning", "order_number"):
        print("Adding order_number to production_planning...")
        cur.execute("ALTER TABLE production_planning ADD COLUMN order_number TEXT")

    con.commit()
    con.close()
    print("Migration successful.")

except Exception as e:
    print(f"Migration failed: {e}")
