import sqlite3
import os

def check_db_path():
    # Check potential paths
    paths = [
        os.getenv("DATABASE_PATH"), # Allow manual override
        'app/data/production.db',
        '/app/data/production.db',
        'production.db'
    ]
    
    for path in paths:
        if path and os.path.exists(path):
            return path
    return None

def add_columns():
    db_path = check_db_path()
    if not db_path:
        print("Database production.db not found in common locations.")
        # If in docker build/init it might not exist yet, which is fine if create_all handles it.
        # But for migration of EXISTING db, we need it.
        return

    print(f"Migrating database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(production_reports)")
    existing_cols = [c[1] for c in cursor.fetchall()]

    new_cols = [
        ('mp_waste_kg', 'FLOAT DEFAULT 0.0'),
        ('mp_waste_image', 'VARCHAR DEFAULT NULL'),
        ('order_number', 'VARCHAR DEFAULT NULL'),
        ('status', 'VARCHAR DEFAULT "Pending"'),
        ('planning_order_ids', 'TEXT DEFAULT NULL'),
        ('cons_type', 'VARCHAR DEFAULT NULL'),
        ('cons_count', 'FLOAT DEFAULT 0.0'),
        ('cons_unit_weight', 'FLOAT DEFAULT 0.0'),
        ('cons_qty', 'FLOAT DEFAULT 0.0')
    ]

    for col_name, col_def in new_cols:
        if col_name not in existing_cols:
            try:
                print(f"Adding column {col_name}...")
                cursor.execute(f"ALTER TABLE production_reports ADD COLUMN {col_name} {col_def}")
                print(f"Successfully added {col_name}.")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
        else:
            print(f"Column {col_name} already exists.")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_columns()
