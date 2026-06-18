import pyodbc

conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;DATABASE=CARMAL_M;UID=profit;PWD=profit;Encrypt=yes;TrustServerCertificate=yes;"

try:
    conn = pyodbc.connect(conn_str, autocommit=True)
    cursor = conn.cursor()

    odp = '0000008890'

    print(f"--- Renglones de ODP {odp} (NSPOrdenProduccionReng) ---")
    cursor.execute(f"SELECT * FROM NSPOrdenProduccionReng WHERE odp_num = '{odp}'")
    cols = [column[0] for column in cursor.description]
    for row in cursor.fetchall():
        print(dict(zip(cols, row)))

    print(f"\n--- Insumos de ODP {odp} (NSPOrdenProduccionInsumo) ---")
    try:
        cursor.execute(f"SELECT * FROM NSPOrdenProduccionInsumo WHERE odp_num = '{odp}'")
        cols = [column[0] for column in cursor.description]
        for row in cursor.fetchall():
            print(dict(zip(cols, row)))
    except Exception as e:
        print(f"No NSPOrdenProduccionInsumo table? {e}")

except Exception as e:
    import traceback
    traceback.print_exc()
