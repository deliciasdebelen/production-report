from check_reng_neto_audit import engine, text

def check_lotes_db():
    with engine.connect() as conn:
        doc = '0000000811'
        print(f"--- REVISIÓN DE LOTES PARA GENE_NUM {doc} ---")
        
        q_ent = text(f"""
        SELECT TOP 10 RTRIM(co_art) as co_art, RTRIM(nro_lote) as nro_lote, cantidad, RTRIM(num_doc) as num_doc, RTRIM(co_alma) as co_alma 
        FROM saLoteEntrada
        WHERE num_doc = '{doc}'
        """)
        try:
            res_ent = conn.execute(q_ent).fetchall()
            print("ENTRADAS (Lote del Articulo Resultante):")
            for r in res_ent:
                print(dict(r._mapping))
            if not res_ent:
                print("No se encontraron entradas.")
        except Exception as e:
            print("Error saLoteEntrada:", e)
            
        q_sal = text(f"""
        SELECT TOP 10 RTRIM(co_art) as co_art, RTRIM(nro_lote) as nro_lote, cantidad, RTRIM(num_doc) as num_doc, RTRIM(co_alma) as co_alma 
        FROM saLoteSalida
        WHERE num_doc = '{doc}'
        """)
        try:
            res_sal = conn.execute(q_sal).fetchall()
            print("\nSALIDAS (Lotes de los Componentes consumidos):")
            for r in res_sal:
                print(dict(r._mapping))
            if not res_sal:
                print("No se encontraron salidas.")
        except Exception as e:
            print("Error saLoteSalida:", e)

if __name__ == '__main__':
    check_lotes_db()
