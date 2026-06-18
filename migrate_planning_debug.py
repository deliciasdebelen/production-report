import sys
import os
import sqlalchemy
from sqlalchemy import create_engine, inspect, text
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.database import Base
from app.models import *

SQLITE_URL = "sqlite:///./production.db"
POSTGRES_URL = "postgresql://app_user:production_password@db:5432/production_db"

def migrate_debug():
    print(f"Debug Migrating ProductionPlanning...")
    
    sqlite_engine = create_engine(SQLITE_URL)
    pg_engine = create_engine(POSTGRES_URL)
    
    inspector = inspect(sqlite_engine)
    table = "production_planning"
    table_model = ProductionPlanning.__table__

    with sqlite_engine.connect() as src_conn:
        with pg_engine.connect() as dst_conn:
            # Check Postgres Count
            count = dst_conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            if count > 0:
                 print(f"Table already has {count} rows. Clearing for debug!")
                 dst_conn.execute(text(f"TRUNCATE {table} RESTART IDENTITY CASCADE"))
                 dst_conn.commit()

            # Fetch Data
            data = src_conn.execute(text(f"SELECT * FROM {table}")).fetchall()
            print(f"Read {len(data)} rows from SQLite.")
            
            # Prepare Insert
            columns_info = inspector.get_columns(table)
            cols = [c['name'] for c in columns_info]
            placeholders = ",".join([f":{c}" for c in cols])
            insert_stmt = text(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})")
            
            clean_rows = []
            for row in data:
                row_dict = dict(zip(cols, row))
                # Boolean fix
                for col in table_model.columns:
                    if isinstance(col.type, sqlalchemy.types.Boolean):
                         if col.name in row_dict:
                             val = row_dict[col.name]
                             if val == 0: row_dict[col.name] = False
                             if val == 1: row_dict[col.name] = True
                clean_rows.append(row_dict)

            try:
                dst_conn.execute(insert_stmt, clean_rows)
                dst_conn.commit()
                print(f"Success! {len(clean_rows)} rows inserted.")
            except Exception as e:
                print(f"Error inserting: {e}")
                # Try inserting row by row to find the bad one
                dst_conn.rollback()
                print("Retrying row by row...")
                for i, row in enumerate(clean_rows):
                    try:
                        dst_conn.execute(insert_stmt, [row])
                        dst_conn.commit()
                    except Exception as row_e:
                        print(f"Failed at row {i} (ID {row.get('id')}): {row_e}")
                        dst_conn.rollback()
                        # print(row) # Might be too verbose

    # Reset seq
    with pg_engine.connect() as conn:
         max_id = conn.execute(text(f"SELECT MAX(id) FROM {table}")).scalar() or 0
         conn.execute(text(f"SELECT setval('{table}_id_seq', {max_id + 1}, false)"))
         print(f"Sequence reset to {max_id + 1}")

if __name__ == "__main__":
    migrate_debug()
