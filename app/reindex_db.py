
import sqlite3
import os

DB_PATH = "/app/production.db"

def main():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    print(f"Connecting to {DB_PATH}...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("Executing VACUUM...")
        cursor.execute("VACUUM")
        
        print("Checking integrity...")
        cursor.execute("PRAGMA integrity_check")
        results = cursor.fetchall()
        for r in results:
            print(r)
            
        conn.close()
        print("Done.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
