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
    # Base.metadata.drop_all(pg_engine) # Clean start
    Base.metadata.create_all(pg_engine)
    
    # 4. Transfer Data (Sorted by dependency)
    inspector = inspect(sqlite_engine) # Need inspector for columns
    sorted_tables = Base.metadata.sorted_tables
    
    with sqlite_engine.connect() as src_conn:
        with pg_engine.connect() as dst_conn:
            for table_model in sorted_tables:
                table = table_model.name
                
                # Check if table exists in output (SQLite)
                # Check if table exists in output (SQLite)
                if not inspector.has_table(table):
                    print(f"Skipping {table} (not in SQLite)")
                    continue

                print(f"Migrating table: {table}...")
                
                # Fetch data
                try:
                    data = src_conn.execute(text(f"SELECT * FROM {table}")).fetchall()
                except Exception as e:
                    print(f"  - Error reading {table}: {e}")
                    continue

                if not data:
                    print(f"  - No data (skipping)")
                    continue
                
                # ALGORITHM:
                # 1. Identify columns
                # Source columns (from SQLite)
                source_columns_info = inspector.get_columns(table)
                source_cols = [c['name'] for c in source_columns_info]
                
                # Target columns (from Model)
                target_cols = [c.name for c in table_model.columns]
                
                # Common columns (Intersection)
                # We only insert columns that exist in BOTH (Source Data & Target Schema)
                common_cols = list(set(source_cols) & set(target_cols))
                
                if not common_cols:
                    print(f"  - No common columns for {table} (Skipping)")
                    continue

                # 2. Construct Insert
                placeholders = ",".join([f":{c}" for c in common_cols])
                insert_stmt = text(f"INSERT INTO {table} ({','.join(common_cols)}) VALUES ({placeholders})")
                
                # 3. Execute
                # Fix Booleans & Filter Data
                clean_rows = []
                for row in data:
                    # Map source row to dict
                    source_dict = dict(zip(source_cols, row))
                    
                    # Filter to common columns
                    final_dict = {}
                    for col_name in common_cols:
                         val = source_dict.get(col_name)
                         # Boolean Fix
                         # Find column type in Model
                         # Optimization: We could map types once, but loop is fine for migration size.
                         model_col = table_model.columns[col_name] 
                         if isinstance(model_col.type, sqlalchemy.types.Boolean):
                             if val == 0: val = False
                             if val == 1: val = True
                         
                         final_dict[col_name] = val
                    
                    clean_rows.append(final_dict)

                try:
                    dst_conn.execute(insert_stmt, clean_rows)
                    dst_conn.commit()
                    print(f"  - {len(clean_rows)} rows copied.")
                except Exception as e:
                    import traceback
                    print(f"  - Error migrating {table}: {e}")
                    traceback.print_exc()
                    dst_conn.rollback()
                    continue

    # 5. Reset Sequences (Important for AutoIncrement)
    print("Resetting sequences...")
    pg_inspector = inspect(pg_engine)
    with pg_engine.connect() as conn:
        for table_model in sorted_tables:
             table = table_model.name
             # Check if table has 'id' column in Postgres
             try:
                 columns = [c['name'] for c in pg_inspector.get_columns(table)]
             except:
                 continue
                 
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
