
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

def run_fix():
    updates = [
        # GUID ...6892: Init 567 -> 762 (+195), Stock 372 -> 567 (+195)
        # Reason: Restore stock to 567 after 195 exit.
        {'guid': '3D7935BE-0BF7-43B7-9DCF-4EDFB03A6892', 'qty': 762.0, 'stock': 567.0},
    ]

    print(f"\n--- FIXING QUANTITIES for {len(updates)} records ---\n", flush=True)

    with engine_a.connect() as conn:
        try:
            trans = conn.begin()
            
            for up in updates:
                print(f"Updating GUID: {up['guid']}", flush=True)
                print(f"  -> Setting cantidad = {up['qty']}", flush=True)
                print(f"  -> Setting stock_actual = {up['stock']}", flush=True)

                query = text(f"""
                    UPDATE saLoteEntrada 
                    SET cantidad = :qty, stock_actual = :stock
                    WHERE rowguid = :guid
                """)
                
                result = conn.execute(query, {
                    "qty": up['qty'], 
                    "stock": up['stock'], 
                    "guid": up['guid']
                })
                print(f"  Rows affected: {result.rowcount}", flush=True)
            
            trans.commit()
            print("Updates committed successfully.", flush=True)
            
        except Exception as e:
            trans.rollback()
            print(f"Error executing update: {e}")
            print("Transaction rolled back.")

if __name__ == "__main__":
    run_fix()
