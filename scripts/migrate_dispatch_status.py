import sqlite3
import os

db_path = "production.db"
backup_path = "production.db.bak_pre_annulment"

if os.path.exists(db_path):
    print("Backing up database...")
    os.system(f"cp {db_path} {backup_path}")
    print(f"Backup created at {backup_path}")

    print("Connecting to database...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("Checking if column 'status' exists...")
        cursor.execute("PRAGMA table_info(logistics_dispatch)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'status' not in columns:
            print("Adding 'status' column to logistics_dispatch...")
            cursor.execute("ALTER TABLE logistics_dispatch ADD COLUMN status VARCHAR(50) DEFAULT 'Activa'")
            conn.commit()
            print("Successfully added 'status' column.")
            
            # Actualizar todos los registros existentes a 'Activa'
            cursor.execute("UPDATE logistics_dispatch SET status = 'Activa' WHERE status IS NULL")
            conn.commit()
            print("Successfully updated existing records to 'Activa'.")
        else:
            print("Column 'status' already exists.")
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()
        print("Done.")
else:
    print(f"Database {db_path} not found!")
