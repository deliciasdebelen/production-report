from check_reng_neto_audit import engine, text

def check_lote_dates():
    with engine.connect() as conn:
        print("--- REVISANDO FECHAS DE LOTES GENERADOS POR 0000000811 (saArtCompuestoGen) ---")
        q_gen = text("""
        SELECT RTRIM(l.numero_lote) as numero_lote, l.fecha_inicio, l.fecha_expiracion, l.revisado, l.cantidad
        FROM saArtCompuestoGen g
        JOIN saLoteEntrada l ON g.rowguid = l.rowguid_reng
        WHERE g.gene_num IN ('0000000811', '0000000810', '0000000809')
        """)
        
        try:
            res_gen = conn.execute(q_gen).fetchall()
            for r in res_gen:
                print(dict(r._mapping))
        except Exception as e:
            print("Error:", e)
            
        print("\n--- REVISANDO FECHAS DE LOTES GENERADOS POR AJUSTES (saAjuste) RECIENTES ---")
        q_aju = text("""
        SELECT TOP 3 RTRIM(l.numero_lote) as numero_lote, l.fecha_inicio, l.fecha_expiracion, l.revisado, l.cantidad, RTRIM(a.ajue_num) as ajue_num
        FROM saAjuste a
        JOIN saAjusteReng r ON a.ajue_num = r.ajue_num
        JOIN saLoteEntrada l ON r.rowguid = l.rowguid_reng
        WHERE a.campo8 = 'MANUFACTURA'
        ORDER BY a.fecha DESC
        """)
        try:
            res_aju = conn.execute(q_aju).fetchall()
            for r in res_aju:
                print(dict(r._mapping))
        except Exception as e:
            print("Error:", e)

if __name__ == '__main__':
    check_lote_dates()
