from check_reng_neto_audit import engine, text

def check_schema():
    with engine.connect() as conn:
        print("--- COLUMNAS EN saLoteEntrada ---")
        q = text("""
        SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME='saLoteEntrada'
        """)
        for r in conn.execute(q).fetchall():
            print(f"  {r.COLUMN_NAME} ({r.DATA_TYPE})")

        print("\\n--- COLUMNAS EN saLoteSalida ---")
        q2 = text("""
        SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME='saLoteSalida'
        """)
        for r in conn.execute(q2).fetchall():
            print(f"  {r.COLUMN_NAME} ({r.DATA_TYPE})")

if __name__ == '__main__':
    check_schema()
