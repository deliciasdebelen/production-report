from check_reng_neto_audit import engine, text

def check_schema():
    with engine.connect() as conn:
        print("--- COLUMNAS EN saArticulo RELACIONADAS A UNIDADES ---")
        q = text("""
        SELECT COLUMN_NAME, DATA_TYPE 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'saArticulo' 
          AND (COLUMN_NAME LIKE '%uni%' OR COLUMN_NAME LIKE '%venta%')
        ORDER BY ORDINAL_POSITION
        """)
        tres = conn.execute(q).fetchall()
        for r in tres:
            print(f"  {r.COLUMN_NAME} ({r.DATA_TYPE})")
            
        print("\n--- EJEMPLO DE UNIDADES MULTIPLES (saArtUnidad) ---")
        q2 = text("""
        SELECT TOP 5 RTRIM(co_art) as co_art, RTRIM(co_uni) as co_uni, equivalencia, uso_ven
        FROM saArtUnidad
        WHERE equivalencia > 1 AND uso_ven = 1
        """)
        try:
            tres2 = conn.execute(q2).fetchall()
            for r in tres2:
                print(dict(r._mapping))
        except Exception as e:
            print("Error saArtUnidad:", e)

if __name__ == '__main__':
    check_schema()
