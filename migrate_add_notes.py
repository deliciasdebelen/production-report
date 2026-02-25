import sqlite3
import os

DB_PATH = "production.db"

def add_notes_column():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE production_planning ADD COLUMN notes TEXT")
        conn.commit()
        print("Column 'notes' added successfully to 'production_planning'.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'notes' already exists.")
        else:
            print(f"Error adding column: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_notes_column()
