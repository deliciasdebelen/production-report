from check_reng_neto_audit import engine, text

def check_factura():
    with engine.connect() as conn:
        print("--- AUDITORIA: saFacturaVentaReng (prec_vta * total_art vs reng_neto) ---")
        
        query1 = text("""
        SELECT COUNT(*) as total_rows
        FROM saFacturaVentaReng
        """)
        total_rows = conn.execute(query1).scalar()
        
        query_count = text("""
        SELECT COUNT(*) 
        FROM saFacturaVentaReng
        WHERE ABS((prec_vta * total_art) - reng_neto) > 0.01
        """)
        
        mismatches = conn.execute(query_count).scalar()
        print(f"Total rows in saFacturaVentaReng: {total_rows}")
        print(f"Rows where (prec_vta * total_art) != reng_neto: {mismatches}")
        
        if mismatches > 0:
            query_details = text("""
            SELECT TOP 20 doc_num, reng_num, co_art, prec_vta, total_art, reng_neto, 
                   (prec_vta * total_art) as calc_val, 
                   ABS((prec_vta * total_art) - reng_neto) as diff,
                   monto_desc, tipo_imp, porc_imp, monto_imp,
                   (prec_vta * total_art) - monto_desc as expected_neto
            FROM saFacturaVentaReng
            WHERE ABS((prec_vta * total_art) - reng_neto) > 0.01
            ORDER BY doc_num DESC
            """)
            res = conn.execute(query_details)
            print(f"{'doc_num':<15} | {'reng_num':<8} | {'prec_vta':<12} | {'total_art':<10} | {'reng_neto':<12} | {'calc_val':<12} | {'diff':<12} | {'monto_desc':<10} | {'expected':<12}")
            print("-" * 120)
            for r in res:
                print(f"{str(r.doc_num):<15} | {str(r.reng_num):<8} | {str(r.prec_vta):<12} | {str(r.total_art):<10} | {str(r.reng_neto):<12} | {str(r.calc_val):<12} | {str(r.diff):<12} | {str(r.monto_desc):<10} | {str(r.expected_neto):<12}")

if __name__ == '__main__':
    check_factura()
