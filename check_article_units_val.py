from check_reng_neto_audit import engine, text

def check_specific():
    with engine.connect() as conn:
        print("--- EJEMPLO SAARTUNIDAD ---")
        q = text("""
        SELECT TOP 5 RTRIM(co_art) as co_art, RTRIM(co_uni) as co_uni, equivalencia, 
               uso_venta, uni_principal, uni_secundaria, uso_secundaria
        FROM saArtUnidad
        WHERE equivalencia > 1 AND uso_venta = 1
        ORDER BY co_art
        """)
        try:
            res = conn.execute(q).fetchall()
            for r in res:
                print(dict(r._mapping))
        except Exception as e:
            print("Error:", e)

if __name__ == '__main__':
    check_specific()
