from check_reng_neto_audit import engine, text

def check_trigger_lote():
    with engine.connect() as conn:
        print("--- DEFINICIÓN DEL TRIGGER ActualizarFechaLote ---")
        q = text("""
        SELECT m.definition
        FROM sys.triggers tr
        JOIN sys.sql_modules m ON tr.object_id = m.object_id
        WHERE tr.name = 'ActualizarFechaLote'
        """)
        res = conn.execute(q).scalar()
        print(res)

if __name__ == '__main__':
    check_trigger_lote()
