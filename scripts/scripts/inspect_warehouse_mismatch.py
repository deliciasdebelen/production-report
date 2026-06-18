
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

def run_inspect_alma():
    mismatches = [
        '62EF63AC-D41A-462D-B37F-D0ECCAF47264',
        '57E79747-7C54-4A37-A661-6927AD8CE988',
        '609D0DF5-9C4C-47F0-9538-3C14B993875B'
    ]

    print(f"\n--- INSPECTING WAREHOUSE MISMATCHES ---\n", flush=True)

    with engine_a.connect() as conn:
        for guid in mismatches:
            print(f"Checking Salida GUID: {guid}", flush=True)
            
            query = text(f"""
                SELECT 
                    LS.rowguid, LS.numero_lote AS Lote_Salida, LS.co_alma AS Alma_Salida,
                    LS.Rowguid_Lote, 
                    LE.numero_lote AS Lote_Entrada, LE.co_alma AS Alma_Entrada
                FROM saLoteSalida LS
                LEFT JOIN saLoteEntrada LE ON LS.Rowguid_Lote = LE.rowguid
                WHERE LS.rowguid = '{guid}'
            """)
            result = conn.execute(query).fetchone()
            
            if not result:
                 # Check rowguid_reng
                query = text(f"""
                SELECT 
                    LS.rowguid, LS.numero_lote AS Lote_Salida, LS.co_alma AS Alma_Salida,
                    LS.Rowguid_Lote, 
                    LE.numero_lote AS Lote_Entrada, LE.co_alma AS Alma_Entrada
                FROM saLoteSalida LS
                LEFT JOIN saLoteEntrada LE ON LS.Rowguid_Lote = LE.rowguid
                WHERE LS.rowguid_reng = '{guid}'
                """)
                result = conn.execute(query).fetchone()

            if result:
                guid_sal, lot_sal, alma_sal, link_guid, lot_ent, alma_ent = result
                
                print(f"  Salida: Lot='{lot_sal}' | Alma='{alma_sal}'")
                print(f"  Entry : Lot='{lot_ent}' | Alma='{alma_ent}'")
                
                if str(alma_sal).strip() != str(alma_ent).strip():
                    print(f"  >> MISMATCH DETECTED: '{alma_sal}' != '{alma_ent}'")
                else:
                    print("  >> NO MISMATCH FOUND")
            else:
                print("  Record not found.")
            
            print("-" * 50)

if __name__ == "__main__":
    run_inspect_alma()
