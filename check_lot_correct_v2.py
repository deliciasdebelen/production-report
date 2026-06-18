import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22

TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"
SQL_DB = "carmal_a"

def sqlcmd(client, sql, db=SQL_DB):
    clean_sql = " ".join(sql.split()).replace('"', '\\"')
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -Q "{clean_sql}" 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode(errors='replace').strip()

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)

    print("=" * 80)
    print("DETALLES DEL ARTÍCULO ME01N00X026")
    print("=" * 80)
    sql_art = "SELECT co_art, art_des FROM saArticulo WHERE co_art = 'ME01N00X026'"
    print(sqlcmd(client, sql_art))

    print("\n" + "=" * 80)
    print("RESUMEN DE ENTRADAS DEL LOTE 20201101A1 EN saLoteEntrada")
    print("=" * 80)
    sql_ent = """
        SELECT le.co_art, le.co_alma, 
               SUM(le.cantidad) as TotalCantidadEntrada, 
               SUM(le.stock_actual) as TotalStockActual,
               MIN(CONVERT(VARCHAR, le.fecha_inicio, 103)) as MinFecIni,
               MAX(CONVERT(VARCHAR, le.fecha_expiracion, 103)) as MaxFecExp
        FROM saLoteEntrada le
        WHERE le.numero_lote = '20201101A1'
        GROUP BY le.co_art, le.co_alma
    """
    print(sqlcmd(client, sql_ent))

    print("\n" + "=" * 80)
    print("DETALLE POR ALMACÉN Y ESTADO (VIGENTE / VENCIDO)")
    print("=" * 80)
    sql_ent_detail = """
        SELECT le.co_art, le.co_alma, le.cantidad, le.stock_actual,
               CONVERT(VARCHAR, le.fecha_inicio, 103) as FecIni,
               CONVERT(VARCHAR, le.fecha_expiracion, 103) as FecExp,
               CASE WHEN le.fecha_expiracion < GETDATE() THEN '*** VENCIDO ***' ELSE 'VIGENTE' END as EstadoVenc
        FROM saLoteEntrada le
        WHERE le.numero_lote = '20201101A1' AND le.stock_actual <> 0
        ORDER BY le.co_alma
    """
    print(sqlcmd(client, sql_ent_detail))

    print("\n" + "=" * 80)
    print("RESUMEN DE SALIDAS DEL LOTE 20201101A1 EN saLoteSalida")
    print("=" * 80)
    sql_sal = """
        SELECT ls.co_art, ls.co_alma, ls.tipo_doc, SUM(ls.cantidad) as TotalCantidadSalida
        FROM saLoteSalida ls
        WHERE ls.numero_lote = '20201101A1'
        GROUP BY ls.co_art, ls.co_alma, ls.tipo_doc
        ORDER BY ls.co_alma
    """
    print(sqlcmd(client, sql_sal))

    client.close()

if __name__ == "__main__":
    run()
