from check_reng_neto_audit import engine, text

def check_schema_full():
    with engine.connect() as conn:
        print("--- COLUMNAS EN saArticulo ---")
        q = text("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'saArticulo' 
          AND (COLUMN_NAME LIKE '%uni%' OR COLUMN_NAME LIKE '%sec%' OR COLUMN_NAME LIKE '%caja%' OR COLUMN_NAME LIKE '%alta%')
        ORDER BY COLUMN_NAME
        """)
        tres = conn.execute(q).fetchall()
        for r in tres:
            print(f"  {r.COLUMN_NAME}")
            
        print("\n--- COLUMNAS EN saArtUnidad ---")
        q2 = text("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'saArtUnidad' 
        ORDER BY COLUMN_NAME
        """)
        try:
            tres2 = conn.execute(q2).fetchall()
            for r in tres2:
                print(f"  {r.COLUMN_NAME}")
        except Exception as e:
            print("Error saArtUnidad:", e)

if __name__ == '__main__':
    check_schema_full()
