import sys
import os
import sqlalchemy
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import Base
from app.models import *  # Import all models to register them

# Config
SQLITE_URL = "sqlite:///./production.db"
# Use localhost for migration since script runs outside container usually, 
# or use service name if running inside. 
# We'll assume running inside 'web' container for simplicity as per plan.
POSTGRES_URL = os.getenv("DATABASE_URL") 

if not POSTGRES_URL or "sqlite" in POSTGRES_URL:
    print("Error: DATABASE_URL is not set to Postgres. Run this inside the container with Postgres configured.")
    # Fallback for dev testing if arg provided
    if len(sys.argv) > 1:
        POSTGRES_URL = sys.argv[1]
    else:
        sys.exit(1)

def migrate():
    print(f"Migrating from {SQLITE_URL} to {POSTGRES_URL}...")
    
    # 1. Connect to SQLite (Source)
    sqlite_engine = create_engine(SQLITE_URL)
    
    # 2. Connect to Postgres (Dest)
    pg_engine = create_engine(POSTGRES_URL)
    
    # 3. Create Tables in Postgres
    print("Creating tables in Postgres...")
    Base.metadata.drop_all(pg_engine) # Clean start
    Base.metadata.create_all(pg_engine)
    
    # 4. Transfer Data
    inspector = inspect(sqlite_engine)
    tables = inspector.get_table_names()
    
    with sqlite_engine.connect() as src_conn:
        with pg_engine.connect() as dst_conn:
            for table in tables:
                print(f"Migrating table: {table}...")
                
                # Fetch data
                data = src_conn.execute(text(f"SELECT * FROM {table}")).fetchall()
                if not data:
                    print(f"  - No data (skipping)")
                    continue
                
                # Insert data
                # We use simple inserts. For complex relationships, order matters (metadata.create_all handles FK order usually, but data insertion might fail if order is wrong).
                # To be safe, we disable FK checks temporarily or order manually.
                # Postgres doesn't have "SET IDENTITY_INSERT". 
                # We accept that creation order matters. "users" usually first.
                
                # ALGORITHM:
                # 1. Get columns
                cols = [c['name'] for c in inspector.get_columns(table)]
                
                # 2. Construct Insert
                placeholders = ",".join([f":{c}" for c in cols])
                insert_stmt = text(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})")
                
                # 3. Execute
                rows = [dict(zip(cols, row)) for row in data]
                dst_conn.execute(insert_stmt, rows)
                dst_conn.commit()
                print(f"  - {len(rows)} rows copied.")

    # 5. Reset Sequences (Important for AutoIncrement)
    print("Resetting sequences...")
    with pg_engine.connect() as conn:
        # Get all sequences and max id
        # This is a bit magic, generic approach:
        for table in tables:
             # Check if table has 'id' column
             columns = [c['name'] for c in inspector.get_columns(table)]
             if 'id' in columns:
                 seq_name = f"{table}_id_seq"
                 # Check if sequence exists
                 exists = conn.execute(text(f"SELECT 1 FROM information_schema.sequences WHERE sequence_name = '{seq_name}'")).fetchone()
                 if exists:
                     max_id = conn.execute(text(f"SELECT MAX(id) FROM {table}")).scalar() or 0
                     conn.execute(text(f"SELECT setval('{seq_name}', {max_id + 1}, false)"))
                     print(f"  - Set {seq_name} to {max_id + 1}")
    
    print("Migration Complete!")

if __name__ == "__main__":
    migrate()
