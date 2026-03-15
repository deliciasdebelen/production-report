
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

def run_deep_inspect():
    guids = [
        '62EF63AC-D41A-462D-B37F-D0ECCAF47264',
        '57E79747-7C54-4A37-A661-6927AD8CE988',
        '609D0DF5-9C4C-47F0-9538-3C14B993875B'
    ]

    print(f"\n--- DEEP INSPECTING MISMATCHES ---\n", flush=True)

    with engine_a.connect() as conn:
        for guid in guids:
            print(f"Searching for GUID: {guid}", flush=True)
            
            # Fetch ALL matches (could be multiple if renglon has split lots)
            query = text(f"""
                SELECT 
                    LS.rowguid, LS.rowguid_reng, LS.numero_lote AS Lot_S, LS.co_alma AS Alma_S,
                    LS.Rowguid_Lote AS Link_To_E,
                    LE.numero_lote AS Lot_E, LE.co_alma AS Alma_E, LE.rowguid AS GUID_E
                FROM saLoteSalida LS
                LEFT JOIN saLoteEntrada LE ON LS.Rowguid_Lote = LE.rowguid
                WHERE LS.rowguid = '{guid}' OR LS.rowguid_reng = '{guid}'
            """)
            results = conn.execute(query).fetchall()
            
            if results:
                print(f"  Found {len(results)} record(s):")
                for i, row in enumerate(results):
                    ls_guid, ls_reng, ls_lot, ls_alma, link, le_lot, le_alma, le_guid = row
                    print(f"    [{i+1}] LS_GUID: {ls_guid}")
                    print(f"        LS_RENG: {ls_reng}")
                    print(f"        Output:  Lot='{ls_lot}' | Alma='{ls_alma}'")
                    print(f"        Input:   Lot='{le_lot}' | Alma='{le_alma}'")
                    print(f"        Link:    {link} -> {le_guid}")
                    
                    if str(ls_alma).strip() != str(le_alma).strip():
                        print(f"        >> MISMATCH: '{ls_alma}' <> '{le_alma}'")
                    else:
                        print(f"        >> MATCH OK.")
            else:
                print("  NO RECORDS FOUND.")
            
            print("-" * 50)

if __name__ == "__main__":
    run_deep_inspect()
