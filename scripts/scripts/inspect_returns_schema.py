
import sys
import os
from sqlalchemy import text

# Add project root to path
sys.path.append(os.getcwd())

from app.external_db import engine_a


def inspect_sales_schema():
    print("Inspecting Sales Tables...", flush=True)
    
    with engine_a.connect() as conn:
        # Check for saFacturaVenta table
        print("\nChecking for saFacturaVenta...")
        try:
            q_cols = text("SELECT name FROM sys.columns WHERE object_id = OBJECT_ID('saFacturaVenta')")
            cols = [r[0] for r in conn.execute(q_cols)]
            print(f"  Columns: {cols}")
        except Exception as e:
            print(f"  Error: {e}")

        # Check for saDocumentoVenta (likely for N/C)
        print("\nChecking for saDocumentoVenta (Credit Notes)...")
        try:
            q_cols = text("SELECT name FROM sys.columns WHERE object_id = OBJECT_ID('saDocumentoVenta')")
            cols = [r[0] for r in conn.execute(q_cols)]
            print(f"  Columns: {cols}")

        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    inspect_sales_schema()
