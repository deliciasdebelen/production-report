"""
Check inventory tables in production PostgreSQL.
"""
import sys
sys.path.insert(0, '/app')

from app.database import engine
from sqlalchemy import text
import json

with engine.connect() as conn:
    # List all inventory-related tables
    tables = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND (table_name LIKE '%invent%' OR table_name LIKE '%stock%')
        ORDER BY table_name
    """)).fetchall()
    
    print("Inventory tables in production:")
    for t in tables:
        tname = t[0]
        count = conn.execute(text(f'SELECT COUNT(*) FROM "{tname}"')).scalar()
        print(f"  {tname}: {count} rows")
        
        if count > 0:
            # Get sample
            rows = conn.execute(text(f'SELECT * FROM "{tname}" LIMIT 3')).fetchall()
            cols = conn.execute(text(f"""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='{tname}' ORDER BY ordinal_position
            """)).fetchall()
            col_names = [c[0] for c in cols]
            print(f"    Columns: {col_names}")
            for r in rows:
                print(f"    Row: {dict(zip(col_names, r))}")
