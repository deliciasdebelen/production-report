from check_reng_neto_audit import engine, text

def check_units():
    with engine.connect() as conn:
        print("--- Revisando Configuración de Unidades de Venta ---")
        q = text("""
        SELECT TOP 10 
            RTRIM(a.co_art) as co_art, 
            RTRIM(a.art_des) as art_des, 
            RTRIM(a.uni_venta) as uni_venta, 
            RTRIM(a.suni_venta) as suni_venta,
            (SELECT MAX(equivalencia) FROM saArtUnidad u WHERE u.co_art = a.co_art AND u.co_uni = a.suni_venta) as equiv_suni
        FROM saArticulo a
        WHERE a.suni_venta IS NOT NULL AND RTRIM(a.suni_venta) <> ''
        """)
        
        try:
            res = conn.execute(q).fetchall()
            for r in res:
                print(dict(r._mapping))
        except Exception as e:
            print("Error:", e)

if __name__ == '__main__':
    check_units()
