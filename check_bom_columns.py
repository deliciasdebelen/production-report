from check_reng_neto_audit import engine, text

def check_missing_columns():
    with engine.connect() as conn:
        print("--- COLUMNAS EN saArtCompuestoReng RELACIONADAS A CANTIDAD ---")
        q = text("""
        SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME='saArtCompuestoReng' AND (COLUMN_NAME LIKE '%cant%' OR COLUMN_NAME LIKE '%total%')
        """)
        for r in conn.execute(q).fetchall():
            print(f"  {r.COLUMN_NAME} ({r.DATA_TYPE})")

        print("\n--- EJEMPLO DE STOCK EN saStockAlmacen ---")
        q2 = text("""
        SELECT TOP 3 RTRIM(co_art) as co_art, RTRIM(co_alma) as co_alma, stock_act 
        FROM saStockAlmacen 
        WHERE stock_act > 0
        """)
        try:
            for r in conn.execute(q2).fetchall():
                print(dict(r._mapping))
        except Exception as e:
            print("Error:", e)

if __name__ == '__main__':
    check_missing_columns()
