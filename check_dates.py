from check_reng_neto_audit import engine, text

def check_dates():
    with engine.connect() as conn:
        q = text("""
        SELECT RTRIM(doc_num) as doc_num, fec_emis, RTRIM(co_mone) as co_mone, tasa
        FROM saDevolucionCliente
        WHERE doc_num IN ('0000000559', '0000000558', '0000000557', '0000000556', '0000000555')
        ORDER BY doc_num DESC
        """)
        
        res = conn.execute(q).fetchall()
        for r in res:
            print(dict(r._mapping))

if __name__ == '__main__':
    check_dates()
