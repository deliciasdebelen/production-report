
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
        
        print("Adding column waste_kg to production_planning...")
        # Check if column exists first to avoid error
        cursor.execute("PRAGMA table_info(production_planning)")
        columns = [info[1] for info in cursor.fetchall()]
        # Check waste_kg
        if 'waste_kg' not in columns:
            cursor.execute("ALTER TABLE production_planning ADD COLUMN waste_kg FLOAT DEFAULT 0.0")
            print("Column waste_kg added.")
        
        # Check color
        if 'color' not in columns:
            cursor.execute("ALTER TABLE production_planning ADD COLUMN color VARCHAR DEFAULT '#3b82f6'")
            print("Column color added.")

        # Check status
        if 'status' not in columns:
            cursor.execute("ALTER TABLE production_planning ADD COLUMN status VARCHAR DEFAULT 'Pending'")
            print("Column status added.")
            
        conn.commit()
        conn.close()
        print("Done.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
