from check_reng_neto_audit import engine, text

def analyze_558():
    with engine.connect() as conn:
        q_fac = text("SELECT RTRIM(doc_num) as doc_num, RTRIM(co_mone) as co_mone, tasa FROM saFacturaVenta WHERE doc_num='0000014233'")
        res_fac = conn.execute(q_fac).fetchone()
        print("====== FACTURA ORIGEN 14233 ======")
        print(dict(res_fac._mapping))
        
        q_dev = text("SELECT RTRIM(doc_num) as doc_num, RTRIM(co_mone) as co_mone, tasa FROM saDevolucionCliente WHERE doc_num='0000000558'")
        res_dev = conn.execute(q_dev).fetchone()
        print("====== DEVOLUCION 558 ======")
        print(dict(res_dev._mapping))

if __name__ == '__main__':
    analyze_558()
