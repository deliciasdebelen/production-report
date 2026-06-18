
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

def run_fix_mismatch():
    mismatches = [
        '62EF63AC-D41A-462D-B37F-D0ECCAF47264',
        '57E79747-7C54-4A37-A661-6927AD8CE988',
        '609D0DF5-9C4C-47F0-9538-3C14B993875B'
    ]

    print(f"\n--- FIXING LOT MISMATCHES ---\n", flush=True)

    with engine_a.connect() as conn:
        try:
            trans = conn.begin()
            
            for guid in mismatches:
                print(f"Processing Salida GUID: {guid}", flush=True)
                
                # 1. Get info
                query = text(f"""
                    SELECT 
                        LS.rowguid, LS.numero_lote, LS.co_art
                    FROM saLoteSalida LS
                    WHERE LS.rowguid = '{guid}' OR LS.rowguid_reng = '{guid}'
                """)
                result = conn.execute(query).fetchone()
                
                if result:
                    real_guid, lot_sal, art = result
                    print(f"  Target Lot: {lot_sal} | Art: {art} | Real GUID: {real_guid}")
                    
                    # 2. Find correct parent
                    q_find = text(f"""
                        SELECT rowguid 
                        FROM saLoteEntrada 
                        WHERE co_art = '{art}' AND numero_lote = '{lot_sal}'
                        ORDER BY fecha_inicio DESC
                    """)
                    candidate = conn.execute(q_find).fetchone()
                    
                    if candidate:
                        new_parent_guid = candidate[0]
                        print(f"  > Found Correct Parent: {new_parent_guid}")
                        
                        # 3. Update
                        q_update = text(f"""
                            UPDATE saLoteSalida
                            SET Rowguid_Lote = :parent
                            WHERE rowguid = :guid
                        """)
                        res = conn.execute(q_update, {"parent": new_parent_guid, "guid": real_guid})
                        print(f"  > Updated {res.rowcount} row(s).")
                    else:
                        print(f"  > ERROR: No parent entry found for lot '{lot_sal}'! Skipping.")
                else:
                    print(f"  Record not found.")
            
            trans.commit()
            print("\n--- FIX COMPLETED SUCCESSFULLY ---")
            
        except Exception as e:
            trans.rollback()
            print(f"Error executing fix: {e}")

if __name__ == "__main__":
    run_fix_mismatch()
