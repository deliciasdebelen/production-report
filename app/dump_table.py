
import sqlite3
import os

DB_PATH = "/app/production.db"

def main():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print(f"--- TABLE DEF ---")
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='production_planning'")
        rows = cursor.fetchall()
        for r in rows:
            print(f"SQL: {r[0]}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
