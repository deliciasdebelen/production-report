import sqlite3

def check_sqlite():
    print("Checking local SQLite (production.db)...")
    try:
        conn = sqlite3.connect("production.db")
        cursor = conn.cursor()
        
        # List tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables: {tables}")
        
        for table in ['users', 'roles', 'production_reports', 'production_planning']:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f" - {table}: {count}")
            else:
                print(f" - {table}: MISSING")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_sqlite()
