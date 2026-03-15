
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

def run_fix_v2():
    mismatches = [
        '62EF63AC-D41A-462D-B37F-D0ECCAF47264',
        '57E79747-7C54-4A37-A661-6927AD8CE988',
        '609D0DF5-9C4C-47F0-9538-3C14B993875B'
    ]

    print(f"\n--- FIXING WAREHOUSE MISMATCHES V2 ---\n", flush=True)

    with engine_a.connect() as conn:
        try:
            # Not using transaction just yet, let's see. Auto-commit?
            # Or use explicit transaction
            trans = conn.begin()
            
            for guid in mismatches:
                print(f"Processing Target GUID: {guid}", flush=True)
                
                # Check current state using rowguid_reng matches
                q_check = text(f"""
                    SELECT 
                        LS.rowguid_reng, LS.co_alma, LS.rowguid
                    FROM saLoteSalida LS
                    WHERE LS.rowguid_reng = '{guid}'
                """)
                row = conn.execute(q_check).fetchone()
                
                if row:
                    print(f"  Found via rowguid_reng. Current Alma: '{row[1]}'")
                    
                    # Target Value
                    target_alma = 'P1-PP'
                    
                    if str(row[1]).strip() != target_alma:
                         print(f"  Updating to '{target_alma}'...")
                         q_upd = text(f"""
                            UPDATE saLoteSalida
                            SET co_alma = :new_alma
                            WHERE rowguid_reng = :guid
                         """)
                         res = conn.execute(q_upd, {"new_alma": target_alma, "guid": guid})
                         print(f"  Rows affected: {res.rowcount}")
                    else:
                        print("  Already matches target.")
                else:
                    print("  NOT FOUND via rowguid_reng. Checking rowguid...")
                    # Fallback check
                    q_check_2 = text(f"SELECT rowguid, co_alma FROM saLoteSalida WHERE rowguid = '{guid}'")
                    row2 = conn.execute(q_check_2).fetchone()
                    if row2:
                         print(f"  Found via rowguid. Current Alma: '{row2[1]}'")
                         if str(row2[1]).strip() != 'P1-PP':
                             print(f"  Updating to 'P1-PP'...")
                             q_upd = text(f"UPDATE saLoteSalida SET co_alma = 'P1-PP' WHERE rowguid = '{guid}'")
                             res = conn.execute(q_upd)
                             print(f"  Rows affected: {res.rowcount}")
                    else:
                        print("  Records NOT FOUND by either GUID.")

            trans.commit()
            print("\n--- DONE ---")
            
        except Exception as e:
            trans.rollback()
            print(f"Error: {e}")

if __name__ == "__main__":
    run_fix_v2()
