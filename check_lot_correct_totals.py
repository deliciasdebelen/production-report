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
    print("DETALLES RESUMIDOS DEL LOTE 20201101A1 EN CARMAL_A")
    print("=" * 80)

    # 1. Articulo
    sql_art = "SELECT co_art, art_des, unidad FROM saArticulo WHERE co_art = 'ME01N00X026'"
    print("[1] Artículo:")
    print(sqlcmd(client, sql_art))

    # 2. Resumen total saLoteEntrada
    sql_totals = """
        SELECT COUNT(*) as CantidadRegistros,
               SUM(cantidad) as TotalOriginalRecibido,
               SUM(stock_actual) as TotalStockDisponibleActual
        FROM saLoteEntrada
        WHERE numero_lote = '20201101A1'
    """
    print("\n[2] Totales Generales en saLoteEntrada:")
    print(sqlcmd(client, sql_totals))

    # 3. Resumen por almacén
    sql_alma = """
        SELECT co_alma, 
               SUM(cantidad) as CantidadEntrada, 
               SUM(stock_actual) as StockDisponible,
               MIN(CONVERT(VARCHAR, fecha_inicio, 103)) as MinFecIni,
               MAX(CONVERT(VARCHAR, fecha_expiracion, 103)) as MaxFecExp
        FROM saLoteEntrada
        WHERE numero_lote = '20201101A1'
        GROUP BY co_alma
    """
    print("\n[3] Totales por Almacén:")
    print(sqlcmd(client, sql_alma))

    # 4. Estado de vencimiento del stock disponible actual
    sql_venc = """
        SELECT co_alma, 
               SUM(stock_actual) as StockDisponibleActual,
               CASE WHEN MIN(fecha_expiracion) < GETDATE() THEN '*** VENCIDO ***' ELSE 'VIGENTE' END as EstadoVenc
        FROM saLoteEntrada
        WHERE numero_lote = '20201101A1' AND stock_actual > 0
        GROUP BY co_alma
    """
    print("\n[4] Estado de Vencimiento de los Lotes con Stock > 0:")
    print(sqlcmd(client, sql_venc))

    # 5. Salidas Totales por Almacén y Tipo Doc
    sql_salidas = """
        SELECT co_alma, tipo_doc, SUM(cantidad) as CantidadSalida
        FROM saLoteSalida
        WHERE numero_lote = '20201101A1'
        GROUP BY co_alma, tipo_doc
        ORDER BY co_alma, tipo_doc
    """
    print("\n[5] Resumen de Consumos/Salidas (saLoteSalida):")
    print(sqlcmd(client, sql_salidas))

    client.close()

if __name__ == "__main__":
    run()
