
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

def run_bulk_fix():
    # List of cases provided by user
    cases = [
        {"lot": "015-25-24092025", "art": "MP01N00X152"},
        {"lot": "013-25-24092025", "art": "MP01N00X152"},
        {"lot": "014-25-24092025", "art": "MP01N00X152"}
    ]

    print(f"\n--- STARTING BULK FIX FOR {len(cases)} CASES ---\n", flush=True)

    with engine_a.connect() as conn:
        try:
            trans = conn.begin()
            
            for case in cases:
                article = case['art']
                lot = case['lot']
                print(f"Processing: Article {article} | Lot {lot}", flush=True)

                # 1. Fetch Entradas
                query_in = text(f"""
                    SELECT rowguid, reng_num, tipo_doc, stock_actual, cantidad 
                    FROM saLoteEntrada 
                    WHERE co_art = '{article}' AND numero_lote = '{lot}'
                """)
                entradas = conn.execute(query_in).fetchall()
                
                if not entradas:
                    print(f"  WARNING: No records found for this lot.", flush=True)
                    continue

                for ent in entradas:
                    ent_guid = ent[0]
                    cantidad_init = ent[4]
                    stock_db = ent[3]
                    
                    # 2. Sum Salidas
                    query_out = text(f"""
                        SELECT COALESCE(SUM(cantidad), 0)
                        FROM saLoteSalida 
                        WHERE Rowguid_Lote = '{ent_guid}'
                    """)
                    sum_salidas = conn.execute(query_out).scalar()
                    
                    # Check consistency
                    stock_calc = cantidad_init - sum_salidas
                    
                    # Logic: If stock_calc is negative (Deficit), we must increase Initial Quantity
                    if stock_calc < -0.00001:
                        deficit = abs(stock_calc)
                        new_qty = sum_salidas # Reset quantity to exactly match exits so balance is 0
                        
                        print(f"  > INCONSISTENCY: Init={cantidad_init} | Exits={sum_salidas} | Calc={stock_calc}", flush=True)
                        print(f"  > ACTION: Updating Quantity to {new_qty} and Stock to 0.0", flush=True)
                        
                        update_query = text(f"""
                            UPDATE saLoteEntrada 
                            SET cantidad = :qty, stock_actual = 0
                            WHERE rowguid = :guid
                        """)
                        conn.execute(update_query, {"qty": new_qty, "guid": ent_guid})
                        print(f"  > FIXED.", flush=True)
                    
                    else:
                        print(f"  > OK: Balance is {stock_calc}. No action needed.", flush=True)
                
                print("-" * 50, flush=True)

            trans.commit()
            print("\n--- BULK FIX COMPLETED SUCCESSFULLY ---", flush=True)

        except Exception as e:
            trans.rollback()
            print(f"Error executing bulk fix: {e}")
            print("Transaction rolled back.")

if __name__ == "__main__":
    run_bulk_fix()
