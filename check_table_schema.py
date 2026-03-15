from check_reng_neto_audit import engine, text

def check_schema():
    with engine.connect() as conn:
        tables = ['saArtCompuestoGen', 'saArtCompuestoGenReng']
        for t in tables:
            print(f"--- COLUMNS FOR {t} ---")
            q = text(f"SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{t}' ORDER BY ORDINAL_POSITION")
            res = conn.execute(q).fetchall()
            for r in res:
                print(f"  {r.COLUMN_NAME} ({r.DATA_TYPE})")

if __name__ == '__main__':
    check_schema()
