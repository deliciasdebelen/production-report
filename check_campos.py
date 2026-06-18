from check_reng_neto_audit import engine, text

def check_campos():
    with engine.connect() as conn:
        print("--- REVISANDO CAMPOS ADICIONALES EN saArtCompuestoGen ---")
        q = text("""
        SELECT TOP 3 RTRIM(gene_num) as gene_num, RTRIM(co_art) as co_art, 
               RTRIM(campo1) as campo1, RTRIM(campo2) as campo2, RTRIM(campo3) as campo3,
               RTRIM(campo4) as campo4, RTRIM(campo5) as campo5, RTRIM(campo6) as campo6,
               RTRIM(campo7) as campo7, RTRIM(campo8) as campo8
        FROM saArtCompuestoGen
        ORDER BY gene_num DESC
        """)
        
        try:
            res = conn.execute(q).fetchall()
            for r in res:
                print(dict(r._mapping))
        except Exception as e:
            print("Error:", e)

if __name__ == '__main__':
    check_campos()
