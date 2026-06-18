from check_reng_neto_audit import engine, text

def check_stock_columns():
    with engine.connect() as conn:
        print("--- COLUMNAS EN saStockAlmacen ---")
        q = text("""
        SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME='saStockAlmacen' AND (COLUMN_NAME LIKE '%stock%' OR COLUMN_NAME LIKE '%cant%')
        """)
        for r in conn.execute(q).fetchall():
            print(f"  {r.COLUMN_NAME} ({r.DATA_TYPE})")

if __name__ == '__main__':
    check_stock_columns()
