
import sys
import os
from sqlalchemy import text
import time

# Add project root to path
sys.path.append(os.getcwd())

try:
    from app.external_db import engine_a
    print("Successfully imported engine_a", flush=True)
except ImportError as e:
    print(f"Failed to import engine_a: {e}")
    sys.exit(1)

def run_fix_force():
    guids = [
        '62EF63AC-D41A-462D-B37F-D0ECCAF47264',
        '57E79747-7C54-4A37-A661-6927AD8CE988',
        '609D0DF5-9C4C-47F0-9538-3C14B993875B'
    ]

    print(f"\n--- FORCE FIXING WAREHOUSE MISMATCHES ---\n", flush=True)

    with engine_a.connect() as conn:
        try:
            trans = conn.begin()
            
            for guid in guids:
                print(f"Target GUID: {guid}", flush=True)
                
                # Check before
                q_check = text(f"SELECT co_alma FROM saLoteSalida WHERE rowguid = '{guid}'")
                val_before = conn.execute(q_check).scalar()
                print(f"  Value BEFORE: '{val_before}'")
                
                # Update
                q_upd = text(f"UPDATE saLoteSalida SET co_alma = 'P1-PP' WHERE rowguid = '{guid}'")
                res = conn.execute(q_upd)
                print(f"  Rows updated: {res.rowcount}")
                
            trans.commit()
            print("\n--- COMMITTED. VERIFYING... ---")
            
            # Verify after commit
            for guid in guids:
                 val_after = conn.execute(text(f"SELECT co_alma FROM saLoteSalida WHERE rowguid = '{guid}'")).scalar()
                 print(f"  GUID {guid} Value AFTER: '{val_after}'")

        except Exception as e:
            trans.rollback()
            print(f"Error: {e}")

if __name__ == "__main__":
    run_fix_force()
