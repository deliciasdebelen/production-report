from check_reng_neto_audit import engine, text

def check_lotes():
    with engine.connect() as conn:
        print("--- ÚLTIMAS GENERACIONES CON SU ROWGUID ---")
        q_gen = text("""
        SELECT TOP 3 RTRIM(gene_num) as gene_num, RTRIM(co_art) as co_art, 
               total_art, rowguid
        FROM saArtCompuestoGen
        ORDER BY gene_num DESC
        """)
        
        try:
            res_gen = conn.execute(q_gen).fetchall()
            for g in res_gen:
                print(f"GEN {g.gene_num} ({g.co_art}): Cantidad {g.total_art}, RowGuid {g.rowguid}")
                
                # Check saLoteEntrada
                q_ent = text(f"""
                SELECT RTRIM(numero_lote) as numero_lote, cantidad, tipo_doc
                FROM saLoteEntrada
                WHERE rowguid_reng = '{g.rowguid}'
                """)
                res_ent = conn.execute(q_ent).fetchall()
                if res_ent:
                    for e in res_ent:
                        print(f"  --> ENTRADA LOTE: {e.numero_lote}, Cant: {e.cantidad}, Tipo: {e.tipo_doc}")
                else:
                    print(f"  --> ALERTA: No hay Lote de ENTRADA para el producto ensamblado.")
                    
                # Check Renglones
                q_det = text(f"""
                SELECT reng_num, RTRIM(co_art) as co_art, total_art, rowguid
                FROM saArtCompuestoGenReng
                WHERE gene_num = '{g.gene_num}'
                """)
                res_det = conn.execute(q_det).fetchall()
                for d in res_det:
                    # Check saLoteSalida
                    q_sal = text(f"""
                    SELECT RTRIM(numero_lote) as numero_lote, cantidad, tipo_doc
                    FROM saLoteSalida
                    WHERE rowguid_reng = '{d.rowguid}'
                    """)
                    res_sal = conn.execute(q_sal).fetchall()
                    lotes_str = ", ".join([f"{s.numero_lote} ({s.cantidad} - {s.tipo_doc})" for s in res_sal])
                    if not lotes_str:
                        lotes_str = "SIN SALIDA DE LOTE"
                    print(f"    Reng {d.reng_num} ({d.co_art}): Cant: {d.total_art} | Lotes Consumidos: {lotes_str}")
        except Exception as e:
            print("Error:", e)

if __name__ == '__main__':
    check_lotes()
