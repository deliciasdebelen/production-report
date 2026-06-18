from check_reng_neto_audit import engine, text

def check_bom_schema():
    with engine.connect() as conn:
        print("--- TABLAS DE ARTICULOS COMPUESTOS ---")
        q = text("""
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_NAME LIKE '%Compuesto%' OR TABLE_NAME LIKE '%Ensamblaje%'
        """)
        try:
            res = conn.execute(q).fetchall()
            for r in res:
                print(r.TABLE_NAME)
        except Exception as e:
            print("Error:", e)

if __name__ == '__main__':
    check_bom_schema()
