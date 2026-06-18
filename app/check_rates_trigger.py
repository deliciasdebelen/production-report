import sys
from sqlalchemy import text
sys.path.append('/app/app')
from external_db import create_engine_for_db

if __name__ == "__main__":
    engine_a = create_engine_for_db('carmal_a')
    engine_n = create_engine_for_db('carmal_n')
    
    query_a = text("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'saTasa'")
    query_n = text("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'snTasa'")
    
    try:
        with engine_a.connect() as conn:
            print("carmal_a.saTasa:")
            for row in conn.execute(query_a):
                print(f"  {row.COLUMN_NAME} ({row.DATA_TYPE})")
                
        with engine_n.connect() as conn:
            print("\ncarmal_n.snTasa:")
            for row in conn.execute(query_n):
                print(f"  {row.COLUMN_NAME} ({row.DATA_TYPE})")
    except Exception as e:
        print(f"Error: {e}")
