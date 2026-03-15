from check_reng_neto_audit import engine, text

def check_devolucion_558():
    with engine.connect() as conn:
        print("--- AUDITORIA: saDevolucionClienteReng doc_num = '0000000558' ---")
        
        query_details = text("""
        SELECT RTRIM(doc_num) as doc_num, reng_num, RTRIM(co_art) as co_art, prec_vta, total_art, reng_neto, 
               (prec_vta * total_art) as calc_val, 
               ABS((prec_vta * total_art) - reng_neto) as diff,
               monto_desc, RTRIM(num_doc) as num_doc_factura, RTRIM(co_precio) as co_precio
        FROM saDevolucionClienteReng
        WHERE doc_num = '0000000558'
        ORDER BY reng_num
        """)
        
        res = conn.execute(query_details).fetchall()
        
        if not res:
            print("Document 0000000558 not found in saDevolucionClienteReng")
            return
            
        print(f"{'doc_num':<12} | {'reng':<4} | {'art':<15} | {'prec_vta':<12} | {'total_art':<10} | {'reng_neto':<12} | {'calc_val':<12} | {'diff':<8} | {'monto_desc':<10} | {'factura_orig'}")
        print("-" * 120)
        
        factura_origen = None
        for r in res:
            if not factura_origen and r.num_doc_factura:
                factura_origen = r.num_doc_factura
            print(f"{str(r.doc_num):<12} | {str(r.reng_num):<4} | {str(r.co_art):<15} | {str(r.prec_vta):<12} | {str(r.total_art):<10} | {str(r.reng_neto):<12} | {str(r.calc_val):<12} | {str(r.diff):<8} | {str(r.monto_desc):<10} | {str(r.num_doc_factura)}")
            
        print("\n--- BUSCANDO FACTURA DE ORIGEN ---")
        if factura_origen:
            print(f"La devolución parece referenciar la factura num_doc={factura_origen}")
            query_fac = text(f"""
            SELECT RTRIM(doc_num) as doc_num, reng_num, RTRIM(co_art) as co_art, prec_vta, total_art, reng_neto, monto_desc
            FROM saFacturaVentaReng
            WHERE doc_num = '{factura_origen}'
            ORDER BY reng_num
            """)
            res_fac = conn.execute(query_fac).fetchall()
            
            if res_fac:
                print(f"{'doc_num':<12} | {'reng':<4} | {'art':<15} | {'prec_vta':<12} | {'total_art':<10} | {'reng_neto':<12} | {'monto_desc':<10}")
                print("-" * 90)
                for f in res_fac:
                    print(f"{str(f.doc_num):<12} | {str(f.reng_num):<4} | {str(f.co_art):<15} | {str(f.prec_vta):<12} | {str(f.total_art):<10} | {str(f.reng_neto):<12} | {str(f.monto_desc):<10}")
            else:
                print(f"ERROR: La factura original {factura_origen} NO SE ENCONTRÓ en la BD.")
        else:
            print("No hay factura de origen especificada en la devolución.")

if __name__ == '__main__':
    check_devolucion_558()
