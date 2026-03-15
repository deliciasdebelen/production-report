from check_reng_neto_audit import engine, text

def check_560():
    with engine.connect() as conn:
        print("--- AUDITORIA: Devolución 0000000560 ---")
        
        q_cab = text("""
        SELECT RTRIM(doc_num) as doc_num, fec_emis, RTRIM(co_mone) as co_mone, tasa,
               total_bruto, monto_desc_glob, total_neto, saldo, anulado
        FROM saDevolucionCliente
        WHERE doc_num = '0000000560'
        """)
        
        try:
            cab = conn.execute(q_cab).fetchone()
            if cab:
                print("CABECERA:")
                print(dict(cab._mapping))
            else:
                print("El documento 0000000560 no existe en saDevolucionCliente.")
                return
        except Exception as e:
            print("Error cabecera:", e)
            
        print("\nRENGLONES:")
        q_det = text("""
        SELECT reng_num, RTRIM(co_art) as co_art, prec_vta, total_art, reng_neto,
               (prec_vta * total_art) as calc_val,
               monto_desc,
               tipo_imp, porc_imp, monto_imp,
               RTRIM(num_doc) as doc_origen
        FROM saDevolucionClienteReng
        WHERE doc_num = '0000000560'
        ORDER BY reng_num
        """)
        
        try:
            res_det = conn.execute(q_det).fetchall()
            for r in res_det:
                diff = abs((r.prec_vta * r.total_art) - r.monto_desc - r.reng_neto)
                # Adding some insight if diff
                flag_diff = " <--- INCONSISTENCIA EN NETO" if diff > 0.01 else ""
                print(f"Reng {r.reng_num} | {r.co_art}")
                print(f"  Cant: {r.total_art} | Precio: {r.prec_vta} | Monto Desc: {r.monto_desc}")
                print(f"  Neto DB: {r.reng_neto} | Neto Esperado (Precio*Cant - Desc): {(r.prec_vta * r.total_art) - r.monto_desc}{flag_diff}")
                print(f"  Impuestos: {r.tipo_imp} ({r.porc_imp}%) -> Monto: {r.monto_imp}")
                print(f"  Factura Origen: {r.doc_origen}")
                print("-" * 50)
                
        except Exception as e:
            print("Error renglones:", e)

if __name__ == '__main__':
    check_560()
