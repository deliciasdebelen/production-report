import sqlite3
import os

DB_PATH = "production.db"

def add_column():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE production_planning ADD COLUMN waste_kg FLOAT DEFAULT 0.0")
        conn.commit()
        print("Column 'waste_kg' added successfully to 'production_planning'.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'waste_kg' already exists.")
        else:
            print(f"Error adding column: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_column()
