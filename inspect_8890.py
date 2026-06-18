import pyodbc

conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;DATABASE=CARMAL_M;UID=profit;PWD=profit;Encrypt=yes;TrustServerCertificate=yes;"

try:
    conn = pyodbc.connect(conn_str, autocommit=True)
    cursor = conn.cursor()

    req_num = '0000008890'
    article = 'MP01D16X05-33'

    print(f"--- Orden de Produccion {req_num} ---")
    cursor.execute(f"SELECT * FROM NSPRequisicion WHERE odp_num = '{req_num}'")
    cols = [column[0] for column in cursor.description]
    reqs = cursor.fetchall()
    req_ids = []
    for row in reqs:
        d = dict(zip(cols, row))
        r_num_str = str(d['req_num']).strip()
        print(f"Req: {r_num_str} Status: {d.get('ESTATUS')} Confirma: {d.get('CONFIRMA')} Traslado: {d.get('tras_num')}")
        req_ids.append(r_num_str)

    for r_num in req_ids:
        print(f"\n--- Renglones de Requisicion {r_num} ---")
        cursor.execute(f"SELECT reng_num, co_art, requerida, solicitada, entregada, alma_ori, alma_des, num_lote, num_envio FROM NSPRequisicionreng WHERE req_num = '{r_num}'")
        cols = [column[0] for column in cursor.description]
        for row in cursor.fetchall():
            d = dict(zip(cols, row))
            print(f"  Reng: {d['reng_num']} Art: {str(d['co_art']).strip()} Req: {d['requerida']} Sol: {d['solicitada']} Ent: {d['entregada']} Lote: {d['num_lote']} Env: {d['num_envio']}")

        print(f"\n--- Lotes Asignados a la Requisicion {r_num} (NSPRequisicion_lote) ---")
        try:
            cursor.execute(f"SELECT * FROM NSPRequisicion_lote WHERE req_num = '{r_num}'")
            cols = [column[0] for column in cursor.description]
            for row in cursor.fetchall():
                d = dict(zip(cols, row))
                print(d)
        except Exception as e:
            print(f"No NSPRequisicion_lote table? {e}")

except Exception as e:
    import traceback
    traceback.print_exc()
