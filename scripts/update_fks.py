import sqlite3
import subprocess

def main():
    try:
        conn = sqlite3.connect('/tmp/production_sqlite_backup.db')
        c = conn.cursor()
        
        print("Updating inventory_headers (user_id 1 -> 58)...")
        c.execute('UPDATE inventory_headers SET user_id=58 WHERE user_id=1')
        print(f"Updated {c.rowcount} rows in inventory_headers.")
        
        print("Updating support_tickets (created_by_id 1 -> 58)...")
        c.execute('UPDATE support_tickets SET created_by_id=58 WHERE created_by_id=1')
        print(f"Updated {c.rowcount} rows in support_tickets.")
        
        conn.commit()
        conn.close()
        print("SQLite updates completed successfully.")
        
        print("Running PostgreSQL migration script...")
        subprocess.run([
            "python3", "/tmp/migrate_sqlite_to_pg_standalone.py",
            "--sqlite", "/tmp/production_sqlite_backup.db",
            "--pg", "postgresql://app_user:production_password@db:5432/production_db"
        ], check=True)
        
    except Exception as e:
        print("ERROR:", e)

if __name__ == '__main__':
    main()
