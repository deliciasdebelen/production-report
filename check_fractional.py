from check_reng_neto_audit import engine, text
from decimal import Decimal

def analyze_fractional_558():
    with engine.connect() as conn:
        q = text("""
        SELECT RTRIM(doc_num) as doc_num, reng_num, RTRIM(co_art) as co_art, 
               prec_vta, total_art, reng_neto
        FROM saDevolucionClienteReng
        WHERE doc_num = '0000000558'
        ORDER BY reng_num
        """)
        
        # Tasa for the document
        tasa = Decimal('414.04550000')
        print(f"--- FÓRMULA DE FACTURACIÓN EN MONEDA EXTRANJERA (Tasa: {tasa}) ---")
        
        res = conn.execute(q).fetchall()
        for r in res:
            # Profit Plus logic for secondary currency pricing:
            # It stores the target currency (USD) equivalent but calculated from the native currency (VES)
            # native_price = prec_vta * tasa
            
            # Let's check how many decimal places it uses for the arithmetic:
            calc_usd = r.prec_vta * r.total_art
            diff = abs(calc_usd - r.reng_neto)
            
            vta = r.prec_vta
            qty = r.total_art
            
            # 1. Native Value approach (VES)
            # Compute total in BS, round to 2, then divide by tasa, round to 2
            calc_ves = round(vta * tasa, 2)
            tot_ves = round(calc_ves * qty, 2)
            back_to_usd = round(tot_ves / tasa, 2)
            
            # 2. Price conversion approach
            # Price in BS given to the user
            base_usd_price = round(vta, 2)
            base_usd_tot = base_usd_price * qty
            
            # Let's see what matches reng_neto perfectly
            print(f"\nRenglon {r.reng_num} - {r.co_art}")
            print(f"  prec_vta={vta}, total_art={qty}")
            print(f"  reng_neto guardado BD = {r.reng_neto}")
            print(f"  Multiplicacion directa (prec_vta * qty) = {calc_usd}")
            print(f"  Diferencia directa = {diff}")
            print(f"  Cálculo VES a USD (Profit Plus Foreign Currency Pattern) = {back_to_usd}")
            if round(r.reng_neto, 2) == round(back_to_usd, 2):
                print("  >> EXACT MATCH: Profit is calculating in native currency and converting back.")
            else:
                # Could it be prec_vta * tasa (no round) * qty / tasa ? 
                ves_raw = vta * tasa
                tot_ves_raw = round(ves_raw * qty, 2)
                usd_raw = round(tot_ves_raw / tasa, 2)
                print(f"  Cálculo VES Crudo (Profit Pattern 2) = {usd_raw}")
                if round(r.reng_neto, 2) == round(usd_raw, 2):
                    print("  >> EXACT MATCH: Profit uses raw unrounded VES for total.")
                    
            # Let's check how it relates to Factura 14233
            
        print("\n--- DETALLES FACTURA ORIGEN ---")
        q_fac = text("""
        SELECT RTRIM(doc_num) as doc_num, reng_num, RTRIM(co_art) as co_art, 
               prec_vta, total_art, reng_neto
        FROM saFacturaVentaReng
        WHERE doc_num = '0000014233'
        ORDER BY reng_num
        """)
        
        res_fac = conn.execute(q_fac).fetchall()
        for f in res_fac:
            print(dict(f._mapping))

if __name__ == '__main__':
    analyze_fractional_558()
