from check_reng_neto_audit import engine, text

def check_trigger_defs():
    with engine.connect() as conn:
        print("--- DEFINICIÓN DEL TRIGGER TrigEstado_saArtCompuestoGen ---")
        q = text("""
        SELECT m.definition
        FROM sys.triggers tr
        JOIN sys.sql_modules m ON tr.object_id = m.object_id
        WHERE tr.name = 'TrigEstado_saArtCompuestoGen'
        """)
        res = conn.execute(q).scalar()
        print(res)
        
        print("\n--- TRIGGERS EN saLoteEntrada y saLoteSalida ---")
        for t in ['saLoteEntrada', 'saLoteSalida', 'saArticulo']:
            q_trig = text(f"""
            SELECT tr.name, m.definition
            FROM sys.triggers tr
            JOIN sys.tables tb ON tr.parent_id = tb.object_id
            JOIN sys.sql_modules m ON tr.object_id = m.object_id
            WHERE tb.name = '{t}'
            """)
            trs = conn.execute(q_trig).fetchall()
            for r in trs:
                print(f"[{t}] Trigger: {r.name}")
                if 'lote' in r.definition.lower() or 'error' in r.definition.lower():
                    print(f"   Posible lógica de validación encontrada en {r.name}")

if __name__ == '__main__':
    check_trigger_defs()
