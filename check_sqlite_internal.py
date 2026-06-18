import sqlite3
import os

DB_PATH = '/app/production.db'

def check():
    print(f"Checking {DB_PATH}...")
    if not os.path.exists(DB_PATH):
        print("Error: DB file not found in container!")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cursor.fetchall()]
        print(f"Found {len(tables)} tables.")
        
        for t in tables:
            try:
                count = cursor.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                print(f"{t}: {count}")
            except Exception as e:
                print(f"{t}: Error {e}")
                
        conn.close()
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    check()
