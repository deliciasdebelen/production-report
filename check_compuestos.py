from check_reng_neto_audit import engine, text

def check_compuestos_lotes():
    with engine.connect() as conn:
        print("--- BUSCANDO TABLAS RELACIONADAS CON ENSAMBLAJE Y LOTES ---")
        
        query_tables = text("""
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE' 
          AND (TABLE_NAME LIKE '%Ensamblaje%' 
               OR TABLE_NAME LIKE '%Compuesto%' 
               OR TABLE_NAME LIKE '%Lote%')
        ORDER BY TABLE_NAME
        """)
        
        tables = conn.execute(query_tables).fetchall()
        for t in tables:
            print(t.TABLE_NAME)

if __name__ == '__main__':
    check_compuestos_lotes()
