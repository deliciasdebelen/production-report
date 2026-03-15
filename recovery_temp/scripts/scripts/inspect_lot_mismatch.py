
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

def run_inspect():
    mismatches = [
        '62EF63AC-D41A-462D-B37F-D0ECCAF47264',
        '57E79747-7C54-4A37-A661-6927AD8CE988',
        '609D0DF5-9C4C-47F0-9538-3C14B993875B'
    ]

    print(f"\n--- INSPECTING LOT MISMATCHES ---\n", flush=True)

    with engine_a.connect() as conn:
        for guid in mismatches:
            print(f"Checking Salida GUID: {guid}", flush=True)
            
            # 1. Get info from saLoteSalida and the linked saLoteEntrada
            # Check rowguid first (most likely)
            query = text(f"""
                SELECT 
                    LS.rowguid, LS.numero_lote, LS.co_art,
                    LS.Rowguid_Lote, 
                    LE.numero_lote AS Lote_Entrada, LE.rowguid AS GUID_Entrada
                FROM saLoteSalida LS
                LEFT JOIN saLoteEntrada LE ON LS.Rowguid_Lote = LE.rowguid
                WHERE LS.rowguid = '{guid}'
            """)
            result = conn.execute(query).fetchone()
            
            if not result:
                # Try rowguid_reng
                 query = text(f"""
                    SELECT 
                        LS.rowguid, LS.numero_lote, LS.co_art,
                        LS.Rowguid_Lote, 
                        LE.numero_lote AS Lote_Entrada, LE.rowguid AS GUID_Entrada
                    FROM saLoteSalida LS
                    LEFT JOIN saLoteEntrada LE ON LS.Rowguid_Lote = LE.rowguid
                    WHERE LS.rowguid_reng = '{guid}'
                """)
                 result = conn.execute(query).fetchone()

            if result:
                guid_sal, lot_sal, art, link_guid, lot_ent, guid_ent = result
                print(f"  FOUND by GUID/Reng!")
                print(f"  Articulo: {art}")
                print(f"  Salida Lot Text: '{lot_sal}'")
                print(f"  Linked Entry Lot: '{lot_ent}' (GUID: {guid_ent})")
                
                if lot_sal.strip() != lot_ent.strip():
                    print(f"  >> MISMATCH DETECTED: '{lot_sal}' != '{lot_ent}'")
                    
                    # 2. Find the CORRECT Entry GUID for the lot name in Salida
                    print(f"  >> Searching for correct parent entry for '{lot_sal}'...")
                    
                    q_find = text(f"""
                        SELECT rowguid, stock_actual, fecha_inicio 
                        FROM saLoteEntrada 
                        WHERE co_art = '{art}' AND numero_lote = '{lot_sal}'
                        ORDER BY fecha_inicio DESC
                    """)
                    candidates = conn.execute(q_find).fetchall()
                    
                    if candidates:
                        for cand in candidates:
                            print(f"     Candidate: {cand[0]} | Stock: {cand[1]} | Date: {cand[2]}")
                    else:
                        print(f"     NO CANDIDATE FOUND for '{lot_sal}' in saLoteEntrada!")
                else:
                    print("  >> NO MISMATCH FOUND (Strange, user reported one?)")
            
            else:
                print("  Record not found in saLoteSalida (checked rowguid and rowguid_reng).")
            
            print("-" * 50)

if __name__ == "__main__":
    run_inspect()
