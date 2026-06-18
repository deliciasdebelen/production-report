
import sys
import os
from sqlalchemy import text

sys.path.append(os.getcwd())
try:
    from app.external_db import engine_a
except ImportError:
    sys.path.append(os.path.join(os.getcwd(), '..'))
    from app.external_db import engine_a

def get_sp_def():
    sp_name = 'RepMovimientoInventarioxArticuloXlote'
    print(f"Fetching definition for {sp_name}...\n")
    
    with engine_a.connect() as conn:
        q = text("SELECT definition FROM sys.sql_modules WHERE object_id = OBJECT_ID(:n)")
        row = conn.execute(q, {"n": sp_name}).fetchone()
        
        if row:
            with open("sp_definition.sql", "w", encoding="utf-8") as f:
                f.write(row[0])
            print("Saved to sp_definition.sql")
        else:
            print("SP NOT FOUND in database.")

if __name__ == "__main__":
    get_sp_def()
