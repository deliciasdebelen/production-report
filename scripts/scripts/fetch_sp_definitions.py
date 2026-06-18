
import sys
import os
from sqlalchemy import text

# Add project root to path
sys.path.append(os.getcwd())

try:
    from app.external_db import engine_a
    print("Successfully imported engine_a", flush=True)
except ImportError as e:
    print(f"Failed to import engine_a: {e}")
    sys.exit(1)

def fetch_sps():
    sps = ['pValidarLoteStock', 'pValidarLoteEntradaSalidaDatos']
    print(f"\n--- Fetching Definitions ---\n", flush=True)

    with engine_a.connect() as conn:
        for sp in sps:
            print(f"--- SP: {sp} ---", flush=True)
            try:
                query = text(f"SELECT definition FROM sys.sql_modules WHERE object_id = OBJECT_ID(:sp_name)")
                result = conn.execute(query, {"sp_name": sp}).fetchone()
                
                if result:
                    print(result[0], flush=True)
                else:
                    print("SP not found.")
            except Exception as e:
                print(f"Error: {e}")
            print("-" * 50, flush=True)

if __name__ == "__main__":
    fetch_sps()
