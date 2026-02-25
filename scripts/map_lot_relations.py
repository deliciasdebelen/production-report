
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

def run_map():
    article = "ME03D17X002"
    lot = "13112025"

    print(f"\n--- Mapping Lots for Article: {article}, Lot: {lot} ---\n", flush=True)

    with engine_a.connect() as conn:
        try:
            # 1. Fetch Entradas with Initial Quantity
            print(f"{'GUID':<36} | {'DOC':<4} | {'INIT':<10} | {'STOCK_DB':<10} | {'CALC':<10} | {'DIFF'}", flush=True)
            print("-" * 100, flush=True)
            
            query_in = text(f"""
                SELECT rowguid, reng_num, tipo_doc, stock_actual, cantidad 
                FROM saLoteEntrada 
                WHERE co_art = '{article}' AND numero_lote = '{lot}'
            """)
            entradas = conn.execute(query_in).fetchall()
            
            for ent in entradas:
                ent_guid = ent[0]
                tipo_doc = ent[2]
                stock_db = ent[3]
                cantidad_init = ent[4]
                
                # 2. Sum Salidas
                query_out = text(f"""
                    SELECT COALESCE(SUM(cantidad), 0)
                    FROM saLoteSalida 
                    WHERE Rowguid_Lote = '{ent_guid}'
                """)
                sum_salidas = conn.execute(query_out).scalar()
                
                stock_calc = cantidad_init - sum_salidas
                diff = stock_db - stock_calc
                
                stock_calc = cantidad_init - sum_salidas
                diff = stock_db - stock_calc
                
                print(f"{ent_guid} | {tipo_doc:<4} | {cantidad_init:<10} | {stock_db:<10} | {stock_calc:<10} | {diff}", flush=True)

                if ent_guid == '3D7935BE-0BF7-43B7-9DCF-4EDFB03A6892':
                    print(f"   *** DETAILED EXITS FOR GUID {ent_guid} ***")
                    q_exits = text(f"SELECT rowguid_reng, tipo_doc, cantidad, numero_lote FROM saLoteSalida WHERE Rowguid_Lote = '{ent_guid}'")
                    exits = conn.execute(q_exits).fetchall()
                    for ex in exits:
                         print(f"     -> EXIT: {ex[0]} | DOC: {ex[1]} | QTY: {ex[2]} | LOT: {ex[3]}")
                    print(f"   *** END DETAILS ***")
                
        except Exception as e:
            print(f"Error executing query: {e}")

if __name__ == "__main__":
    run_map()
