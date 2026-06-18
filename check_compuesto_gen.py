from check_reng_neto_audit import engine, text

def check_compuesto_gen():
    with engine.connect() as conn:
        print("--- ÚLTIMAS GENERACIONES DE ARTICULOS COMPUESTOS ---")
        q_gen = text("""
        SELECT TOP 5 RTRIM(doc_num) as doc_num, fec_emis, RTRIM(co_art) as co_art, cantidad, 
               RTRIM(nro_lote) as nro_lote, anulado
        FROM saArtCompuestoGen
        ORDER BY doc_num DESC
        """)
        
        try:
            res = conn.execute(q_gen).fetchall()
            for r in res:
                print(dict(r._mapping))
                doc = r.doc_num
                print(f"  Detalles para doc {doc}:")
                q_det = text(f"""
                SELECT reng_num, RTRIM(co_art) as co_art, cantidad, RTRIM(nro_lote) as nro_lote
                FROM saArtCompuestoGenReng
                WHERE doc_num = '{doc}'
                ORDER BY reng_num
                """)
                res_det = conn.execute(q_det).fetchall()
                for d in res_det:
                    print(f"    Reng {d.reng_num} - {d.co_art}: Cantidad {d.cantidad}, Lote {d.nro_lote}")
        except Exception as e:
            print("No se pudo consultar detalle de saArtCompuestoGen:", e)

if __name__ == '__main__':
    check_compuesto_gen()
