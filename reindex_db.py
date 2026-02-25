
from sqlalchemy import create_engine, text

# Use local path mapped relative to script? 
# Remote execution needs to access valid DB path or correct engine.
# deploy_prod.py runs on host, but reindex needs python env?
# I'll create a script that runs INSIDE the container or uses the local DB file on host?
# The DB file is `./production.db` on host. I can access it using sqlite3 CLI on host or python.
# But DB is locked by container?
# Safer to run via app container environment.

import sys
sys.path.append('/app') # Assuming logic

# Actually simpler: connect using standard sqlite.
import sqlite3

DB_PATH = "production.db" # Local relative path on host if mapped

def main():
    print(f"Connecting to {DB_PATH}...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("Executing REINDEX production_planning...")
        cursor.execute("REINDEX production_planning")
        
        print("Checking integrity...")
        cursor.execute("PRAGMA integrity_check")
        print(cursor.fetchall())
        
        # Check order numbers
        print("Dumping order_number values:")
        cursor.execute("SELECT id, order_number FROM production_planning")
        rows = cursor.fetchall()
        for r in rows:
            print(r)
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
