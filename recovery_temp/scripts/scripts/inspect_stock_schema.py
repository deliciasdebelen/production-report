
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import text
from app.external_db import engine_a

def inspect_schema():
    print("Inspecting saStockAlmacen columns...")
    with engine_a.connect() as conn:
        q = text("SELECT name FROM sys.columns WHERE object_id = OBJECT_ID('saStockAlmacen')")
        rows = conn.execute(q).fetchall()
        print([r[0] for r in rows])

if __name__ == "__main__":
    inspect_schema()
