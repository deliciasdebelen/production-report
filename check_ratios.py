from check_reng_neto_audit import engine, text
from decimal import Decimal

def analyze_ratios_558():
    with engine.connect() as conn:
        q = text("""
        SELECT RTRIM(doc_num) as doc_num, reng_num, RTRIM(co_art) as co_art, 
               prec_vta, total_art, reng_neto
        FROM saDevolucionClienteReng
        WHERE doc_num = '0000000558'
        ORDER BY reng_num
        """)
        
        res = conn.execute(q).fetchall()
        
        print("--- REVERSE ENGINEERING TASA FROM VES TOTAL ---")
        # Let's see what the original TASA for the products actually was in the system
        # If they had a different original tasa, the conversion back to BS and then to the new USD tasa would cause this.
        
        # Current dev tasa
        tasa_dev = Decimal('414.04550000')
        
        for r in res:
            calc_usd_expected = r.prec_vta * r.total_art
            
            # If the reng_neto was derived by dividing a VES amount by 414.0455
            # Then the VES amount was:
            ves_amount = round(r.reng_neto * tasa_dev, 2)
            
            # If the ves amount was calculated using the same total_art and prec_vta, what was the tasa used to calculate it?
            # ves_amount = prec_vta * total_art * tasa_orig
            # tasa_orig = ves_amount / (prec_vta * total_art)
            
            tasa_orig = ves_amount / calc_usd_expected
            
            print(f"Reng {r.reng_num} ({r.co_art}):")
            print(f"  Expected USD: {calc_usd_expected}")
            print(f"  Actual USD Neto: {r.reng_neto}")
            print(f"  Implied VES Amount (Neto * {tasa_dev}): {ves_amount}")
            print(f"  Implied Original Tasa used for the VES Amount: {tasa_orig}")
            print(f"  Difference between implied and dev tasa: {tasa_orig - tasa_dev}")
            print("-" * 40)

if __name__ == '__main__':
    analyze_ratios_558()
