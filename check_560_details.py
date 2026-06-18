from check_reng_neto_audit import engine, text

def check_560_details():
    with engine.connect() as conn:
        print("--- AUDITORIA: Devolución 0000000560 y Factura Origen 0000014037 ---")
        
        q_det = text("""
        SELECT reng_num, RTRIM(co_art) as co_art, prec_vta, total_art, reng_neto,
               monto_desc, tipo_imp, porc_imp, monto_imp,
               (prec_vta * total_art) - monto_desc as expected_bruto,
               ((prec_vta * total_art) - monto_desc) * (porc_imp / 100) as expected_imp
        FROM saDevolucionClienteReng
        WHERE doc_num = '0000000560'
        ORDER BY reng_num
        """)
        
        try:
            res_det = conn.execute(q_det).fetchall()
            print("DEVOLUCION RENGLONES:")
            for r in res_det:
                print(dict(r._mapping))
                
        except Exception as e:
            print("Error renglones dev:", e)
            
        print("\nFACTURA ORIGEN RENGLONES:")
        q_fac = text("""
        SELECT reng_num, RTRIM(co_art) as co_art, prec_vta, total_art, reng_neto,
               monto_desc, tipo_imp, porc_imp, monto_imp,
               (prec_vta * total_art) - monto_desc as expected_bruto,
               ((prec_vta * total_art) - monto_desc) * (porc_imp / 100) as expected_imp
        FROM saFacturaVentaReng
        WHERE doc_num = '0000014037'
        ORDER BY reng_num
        """)
        
        try:
            res_fac = conn.execute(q_fac).fetchall()
            for r in res_fac:
                print(dict(r._mapping))
                
        except Exception as e:
            print("Error renglones fac:", e)
            
        print("\nCABECERA DEVOLUCION:")
        q_cab = text("""
        SELECT total_bruto, monto_desc_glob, total_neto, monto_imp, saldo
        FROM saDevolucionCliente
        WHERE doc_num = '0000000560'
        """)
        try:
            cab = conn.execute(q_cab).fetchone()
            print(dict(cab._mapping))
        except Exception as e:
            print(e)
            
        print("\nCABECERA FACTURA ORIGEN:")
        q_cab_f = text("""
        SELECT total_bruto, monto_desc_glob, total_neto, monto_imp, saldo
        FROM saFacturaVenta
        WHERE doc_num = '0000014037'
        """)
        try:
            cab_f = conn.execute(q_cab_f).fetchone()
            print(dict(cab_f._mapping))
        except Exception as e:
            print(e)

if __name__ == '__main__':
    check_560_details()
