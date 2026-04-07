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

def test_sp(db_name, invoice_num):
    engine = create_engine_for_db(db_name)
    try:
        with engine.connect() as conn:
            query = text("EXEC RepFormatoFacturaVentaOM_Consolidada_V2_CV @cCo_Numero_d = :inv, @cCo_Numero_h = :inv")
            result = conn.execute(query, {"inv": invoice_num})
            rows = result.fetchall()
            
            if not rows:
                print(f"No results found for invoice {invoice_num}.")
                return

            columns = result.keys()
            
            print(f"Found {len(rows)} grouped items for invoice {invoice_num}.")
            
            # Print header level totals from the first row (since they are repeated/averaged)
            first_row = dict(zip(columns, rows[0]))
            
            print("\nHeader Totals (BS):")
            print(f"Total Bruto: {first_row.get('total_bruto')}")
            print(f"Monto Imp: {first_row.get('monto_imp')}")
            print(f"Total Neto: {first_row.get('total_neto')}")
            
            print("\nHeader Totals (USD):")
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
            
            print("\nRenglones Summed Totals:")
            print(f"Sum Reng Neto (BS): {sum_reng_neto}")
            print(f"Sum Reng Neto (USD): {sum_reng_neto2}")
            print(f"Sum Reng Monto Imp (BS): {sum_reng_monto_imp}")
            print(f"Sum Reng Monto Imp (USD): {sum_reng_monto_imp2}")
            
            print(f"\nExento/Sin Impuesto Calculated:")
            print(f"Sum Reng Monto Sinimp (BS): {sum_reng_monto_sinimp}")
            print(f"Sum Reng Monto Sinimp (USD): {sum_reng_monto_sinimp2}")

            # Dump standard dict representation of the first couple lines just in case
            print("\nRow 1 Details (JSON sample):")
            r1_dict = dict(zip(columns, rows[0]))
            print(json.dumps(r1_dict, cls=DecimalEncoder, indent=2))
            
    except Exception as e:
        print(f"Error testing in {db_name}: {e}")

if __name__ == "__main__":
    test_sp('carmal_a', '0000014764')
