from check_reng_neto_audit import engine, text

def check_bom():
    with engine.connect() as conn:
        print("--- COLUMNAS saArtCompuesto ---")
        q1 = text("""
        SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='saArtCompuesto'
        """)
        for r in conn.execute(q1).fetchall():
            print(f"  {r.COLUMN_NAME} ({r.DATA_TYPE})")

        print("\n--- COLUMNAS saArtCompuestoReng ---")
        q2 = text("""
        SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='saArtCompuestoReng'
        """)
        for r in conn.execute(q2).fetchall():
            print(f"  {r.COLUMN_NAME} ({r.DATA_TYPE})")
            
        print("\n--- EJEMPLO DE UN ARTICULO COMPUESTO ---")
        q3 = text("""
        SELECT TOP 1 RTRIM(h.co_art) as p_terminado, RTRIM(d.co_art) as componente, d.cantidad
        FROM saArtCompuesto h
        JOIN saArtCompuestoReng d ON h.co_art = d.co_art
        """)
        res = conn.execute(q3).fetchall()
        for r in res:
            print(dict(r._mapping))

if __name__ == '__main__':
    check_bom()
