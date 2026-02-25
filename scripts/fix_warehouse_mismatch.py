
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

def run_fix_warehouse():
    mismatches = [
        '62EF63AC-D41A-462D-B37F-D0ECCAF47264',
        '57E79747-7C54-4A37-A661-6927AD8CE988',
        '609D0DF5-9C4C-47F0-9538-3C14B993875B'
    ]

    print(f"\n--- FIXING WAREHOUSE MISMATCHES ---\n", flush=True)

    with engine_a.connect() as conn:
        try:
            trans = conn.begin()
            
            for guid in mismatches:
                print(f"Processing Salida GUID: {guid}", flush=True)
                
                # 1. Get info including linked parent warehouse
                query = text(f"""
                    SELECT 
                        LS.rowguid, LS.co_alma AS Alma_Salida,
                        LE.co_alma AS Alma_Entrada
                    FROM saLoteSalida LS
                    LEFT JOIN saLoteEntrada LE ON LS.Rowguid_Lote = LE.rowguid
                    WHERE LS.rowguid = '{guid}' OR LS.rowguid_reng = '{guid}'
                """)
                result = conn.execute(query).fetchone()
                
                if result:
                    real_guid, alma_sal, alma_ent = result
                    print(f"  Current Alma: '{alma_sal}' | Component Alma: '{alma_ent}'")
                    
                    if alma_ent and alma_sal.strip() != alma_ent.strip():
                        print(f"  > Fixing Mismatch: Setting to '{alma_ent}'")
                        
                        # 2. Update
                        q_update = text(f"""
                            UPDATE saLoteSalida
                            SET co_alma = :new_alma
                            WHERE rowguid = :guid
                        """)
                        res = conn.execute(q_update, {"new_alma": alma_ent, "guid": real_guid})
                        print(f"  > Updated {res.rowcount} row(s).")
                    else:
                        print(f"  > No mismatch to fix (or parent not found).")
                else:
                    print(f"  Record not found.")
            
            trans.commit()
            print("\n--- FIX COMPLETED SUCCESSFULLY ---")
            
        except Exception as e:
            trans.rollback()
            print(f"Error executing fix: {e}")

if __name__ == "__main__":
    run_fix_warehouse()
