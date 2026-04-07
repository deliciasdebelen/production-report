import sys
import os
import json
from decimal import Decimal
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.external_db import create_engine_for_db
from sqlalchemy import text

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        # handle dates and other non-json serializable types
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super(DecimalEncoder, self).default(obj)

def test_sp(db_name, dev_num):
    engine = create_engine_for_db(db_name)
    # the procedure pad the string to 20 chars
    dev_num_padded = dev_num.strip().zfill(20)
    dev_num_str = "{:<20}".format(dev_num.strip().zfill(10)) 
    print(f"Testing Devolution: '{dev_num_str}'")
    try:
        with engine.connect() as conn:
            query = text("EXEC RepFormatoDevolucionClienteOM_Lote_V2_CV @sCo_Numero_d = :inv, @sCo_Numero_h = :inv")
            result = conn.execute(query, {"inv": dev_num_str})
            rows = result.fetchall()
            
            if not rows:
                print(f"No results found for devolution {dev_num_str}.")
                return

            columns = result.keys()
            print(f"Found {len(rows)} returned rows for devolution {dev_num_str}.")
            
            # Print header level totals from the first row (since they are repeated/averaged)
            first_row = dict(zip(columns, rows[0]))
            
            print("\n------------------------------")
            print("HEADER TOTALS (BS)")
            print(f"Total Bruto: {first_row.get('total_bruto')}")
            print(f"Monto Imp: {first_row.get('monto_imp')}")
            print(f"Total Neto: {first_row.get('total_neto')}")
            
            print("\n------------------------------")
            print("HEADER TOTALS (USD)")
            print(f"Total Bruto USD: {first_row.get('total_bruto2')}")
            print(f"Monto Imp USD: {first_row.get('monto_imp2')}")
            print(f"Total Neto USD: {first_row.get('total_neto2')}")
            print(f"Exchange Rate (Tasa): {first_row.get('tasa')}")
            
            # Sum up renglones
            sum_reng_neto = sum(row.reng_neto or 0 for row in rows)
            sum_reng_neto2 = sum(row.reng_neto2 or 0 for row in rows)
            sum_reng_monto_imp = sum(row.reng_monto_imp or 0 for row in rows)
            sum_reng_monto_imp2 = sum(row.reng_monto_imp2 or 0 for row in rows)

            sum_reng_monto_sinimp = sum(row.reng_monto_sinimp or 0 for row in rows)
            sum_reng_monto_sinimp2 = sum(row.reng_monto_sinimp2 or 0 for row in rows)
            
            print("\n------------------------------")
            print("RENGLONES AGGREGATED TOTALS")
            print(f"Sum Reng Neto (BS): {sum_reng_neto}")
            print(f"Sum Reng Neto (USD): {sum_reng_neto2}")
            print(f"Sum Reng Monto Imp (BS): {sum_reng_monto_imp}")
            print(f"Sum Reng Monto Imp (USD): {sum_reng_monto_imp2}")
            
            print(f"\nExento/Sin Impuesto Calculated (From New Bugfix):")
            print(f"Sum Reng Monto Sinimp (BS): {sum_reng_monto_sinimp}")
            print(f"Sum Reng Monto Sinimp (USD): {sum_reng_monto_sinimp2}")

            # Dump standard dict representation of the lines to check variables
            print("\n==============================")
            print("JSON OUTPUT FOR ROW LINE 1")
            r1_dict = dict(zip(columns, rows[0]))
            print(json.dumps(r1_dict, cls=DecimalEncoder, indent=2))
            
    except Exception as e:
        print(f"Error testing in {db_name}: {e}")

if __name__ == "__main__":
    test_sp('carmal_a', '573')
