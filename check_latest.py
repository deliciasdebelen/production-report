from check_reng_neto_audit import engine, text

def check_latest():
    with engine.connect() as conn:
        q = text("""
        SELECT TOP 3 RTRIM(doc_num) as doc_num, fec_emis
        FROM saDevolucionCliente
        ORDER BY doc_num DESC
        """)
        
        res = conn.execute(q).fetchall()
        for r in res:
            print(dict(r._mapping))

if __name__ == '__main__':
    check_latest()
