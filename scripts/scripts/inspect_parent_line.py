
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

def inspect_docs():
    docs = ['0000012073', '0000012160']  # identified from previous step

    print(f"\n--- INSPECTING FULL DOCUMENTS ---\n", flush=True)

    with engine_a.connect() as conn:
        for doc in docs:
            print(f"Document: {doc}", flush=True)
            
            # List all lines
            q_lines = text(f"""
                SELECT rowguid, reng_num, co_art, total_art
                FROM saTrasladoReng 
                WHERE tras_num = '{doc}'
                ORDER BY reng_num
            """)
            lines = conn.execute(q_lines).fetchall()
            
            print(f"  Total Lines: {len(lines)}")
            for line in lines:
                l_guid, l_num, l_art, l_qty = line
                print(f"    Ln {l_num}: {l_art} (Qty: {l_qty})")
                
                # Check linked Lot Output for this line
                q_lot = text(f"""
                    SELECT LS.numero_lote, LS.co_alma, LE.co_alma
                    FROM saLoteSalida LS
                    LEFT JOIN saLoteEntrada LE ON LS.Rowguid_Lote = LE.rowguid
                    WHERE LS.rowguid_reng = '{l_guid}'
                """)
                lot_rows = conn.execute(q_lot).fetchall()
                for lr in lot_rows:
                    print(f"      > Lot: {lr[0]} | SalidaAlma: '{lr[1]}' | EntradaAlma: '{lr[2]}'")
            
            print("-" * 50)

if __name__ == "__main__":
    inspect_docs()
