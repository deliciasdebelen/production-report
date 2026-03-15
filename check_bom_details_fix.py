from check_reng_neto_audit import engine, text

def check_bom_fix():
    with engine.connect() as conn:
        print("--- EJEMPLO DE UN ARTICULO COMPUESTO ---")
        q = text("""
        SELECT TOP 3 
            RTRIM(h.co_art) as p_terminado, 
            RTRIM(d.co_art) as componente, 
            d.cantidad, 
            RTRIM(d.co_uni) as uni_componente
        FROM saArtCompuesto h
        JOIN saArtCompuestoReng d ON h.co_artc = d.co_artc
        """)
        try:
            res = conn.execute(q).fetchall()
            for r in res:
                print(dict(r._mapping))
        except Exception as e:
            print("Error:", e)
            
        print("\n--- EJEMPLO DE STOCK ---")
        q2 = text("""
        SELECT TOP 3 RTRIM(co_art) as co_art, stock_act 
        FROM saArticulo 
        WHERE stock_act > 0
        """)
        try:
            res2 = conn.execute(q2).fetchall()
            for r in res2:
                print(dict(r._mapping))
        except Exception as e:
            print("Error:", e)

if __name__ == '__main__':
    check_bom_fix()
