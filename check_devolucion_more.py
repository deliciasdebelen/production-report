from check_reng_neto_audit import engine, text

def check_devolucion_more():
    with engine.connect() as conn:
        print("--- MAS DETALLES DE DEVOLUCION 0000000558 ---")
        
        query = text("""
        SELECT RTRIM(doc_num) as doc_num, reng_num, RTRIM(co_art) as co_art, 
               prec_vta, total_art, reng_neto, 
               monto_desc, monto_desc_glob = 0.0, monto_reca = 0.0, monto_imp,
               costo_pro = 0.0, costo_di = 0.0,
               tasa = 0.0,
               tipo_imp,
               porc_imp
        FROM saDevolucionClienteReng
        WHERE doc_num = '0000000558'
        ORDER BY reng_num
        """)
        
        res = conn.execute(query).fetchall()
        for r in res:
            print(dict(r._mapping))
            
        print("\n--- BUSCANDO GLOBAL DESCUENTO ---")
        try:
            query2 = text("""
            SELECT RTRIM(doc_num) as doc_num, desc_glob, monto_desc_glob
            FROM saDevolucionCliente
            WHERE doc_num = '0000000558'
            """)
            res2 = conn.execute(query2).fetchall()
            for r in res2:
                print("DEVOLUCION:", dict(r._mapping))
        except Exception as e:
            print("No desc_glob en DevolucionCabecera", e)
            
        print("\n--- BUSCANDO GLOBAL FACTURA ---")
        try:
            query3 = text("""
            SELECT RTRIM(doc_num) as doc_num, desc_glob, monto_desc_glob
            FROM saFacturaVenta
            WHERE doc_num = '0000014233'
            """)
            res3 = conn.execute(query3).fetchall()
            for r in res3:
                print("FACTURA:", dict(r._mapping))
        except Exception as e:
            print("No desc_glob en FacturaCabecera", e)

if __name__ == '__main__':
    check_devolucion_more()
