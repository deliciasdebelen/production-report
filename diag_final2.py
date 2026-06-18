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

    print("=" * 70)
    print("DIAGNÓSTICO FINAL - Compuesto 32 / ODP 0000000946")
    print("=" * 70)

    # 1. Detalles de la generación 946
    print("\n[1] GENERACIÓN 0000000946")
    sql1 = """
        SELECT gene_num, co_art, co_alma, CONVERT(VARCHAR,fecha,103) AS fecha, 
               total_art, gene_art
        FROM saArtCompuestoGen WHERE gene_num = '0000000946'
    """
    print(sqlcmd(client, sql1))

    # 2. Renglones con co_art para ver si es MP04N00X021 el que falla
    print("\n[2] RENGLONES GEN 0000000946 - ¿cuál no tiene lote_asignado?")
    sql2 = """
        SELECT reng_num, co_art, co_alma, co_uni, total_art, 
               lote_asignado,
               CASE WHEN lote_asignado = 1 THEN 'SI' ELSE 'NO ASIGNADO' END AS estado_lote
        FROM saArtCompuestoGenReng
        WHERE gene_num = '0000000946'
        ORDER BY reng_num
    """
    print(sqlcmd(client, sql2))

    # 3. LOTES DISPONIBLES de MP04N00X021 en almacén P1-PS (donde busca Profit)
    print("\n[3] LOTES VIGENTES MP04N00X021 EN ALMACÉN P1-PS")
    sql3 = """
        SELECT numero_lote, co_art, co_alma, 
               CONVERT(VARCHAR, fecha_inicio, 103) AS FecIni,
               CONVERT(VARCHAR, fecha_expiracion, 103) AS FecExp,
               cantidad, stock_actual,
               CASE WHEN fecha_expiracion < GETDATE() THEN '*** VENCIDO ***' ELSE 'VIGENTE' END AS EstVenc
        FROM saLoteEntrada
        WHERE co_art = 'MP04N00X021'
          AND co_alma = 'P1-PS'
          AND stock_actual > 0
        ORDER BY fecha_expiracion DESC
    """
    result3 = sqlcmd(client, sql3)
    print(result3 if result3.strip() else ">>> NO HAY LOTES CON STOCK EN P1-PS <<<")

    # 4. TODOS los lotes de MP04N00X021 en TODOS los almacenes con stock
    print("\n[4] LOTES MP04N00X021 CON stock_actual > 0 EN TODOS LOS ALMACENES")
    sql4 = """
        SELECT numero_lote, co_art, co_alma,
               CONVERT(VARCHAR, fecha_expiracion, 103) AS FecExp,
               stock_actual,
               CASE WHEN fecha_expiracion < GETDATE() THEN '*** VENCIDO ***' ELSE 'VIGENTE' END AS EstVenc
        FROM saLoteEntrada
        WHERE co_art = 'MP04N00X021'
          AND stock_actual > 0
        ORDER BY co_alma, fecha_expiracion DESC
    """
    print(sqlcmd(client, sql4))

    # 5. Stock en saStockAlmacen para MP04N00X021
    print("\n[5] STOCK TOTAL POR ALMACÉN (saStockAlmacen) - MP04N00X021")
    sql5 = """
        SELECT co_alma, co_art, tipo, stock
        FROM saStockAlmacen
        WHERE co_art = 'MP04N00X021'
        ORDER BY co_alma, tipo
    """
    print(sqlcmd(client, sql5))

    # 6. Existe traslado pendiente de ácido cítrico hacia P1-PS?
    print("\n[6] TRASLADOS RECIENTES INVOLUCRANDO MP04N00X021 (saTraslado)")
    # Discover columns
    sql6cols = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'saTraslado' ORDER BY ORDINAL_POSITION"
    print("Columnas saTraslado:", sqlcmd(client, sql6cols)[:200])

    # 7. Artículo MP04N00X021 - maneja_lote_venc flag
    print("\n[7] CONFIGURACIÓN DEL ARTÍCULO MP04N00X021 (maneja_lote_venc)")
    sql7 = """
        SELECT co_art, art_des, maneja_lote, maneja_lote_venc, tipo
        FROM saArticulo
        WHERE co_art = 'MP04N00X021'
    """
    print(sqlcmd(client, sql7))

    # 8. Comprobacion: el lote que Profit muestra (3AX2112019) en P1-PS
    print("\n[8] LOTE 3AX2112019 EN ALMACÉN P1-PS SOLAMENTE")
    sql8 = """
        SELECT numero_lote, co_art, co_alma,
               CONVERT(VARCHAR, fecha_expiracion, 103) AS FecExp,
               cantidad, stock_actual,
               CASE WHEN fecha_expiracion < GETDATE() THEN '*** VENCIDO ***' ELSE 'VIGENTE' END AS EstVenc
        FROM saLoteEntrada
        WHERE numero_lote = '3AX2112019'
          AND co_alma = 'P1-PS'
    """
    result8 = sqlcmd(client, sql8)
    print(result8 if result8.strip() and 'rows affected' not in result8.replace('(0 rows affected)', '') 
          else ">>> LOTE 3AX2112019 NO EXISTE EN P1-PS <<<")
    print(result8)

    # 9. Cómo llegó ese lote a P1-PS: buscar en saLoteSalida
    print("\n[9] MOVIMIENTOS DEL LOTE 3AX2112019 EN saLoteSalida (P1-PS)")
    sql9 = """
        SELECT ls.tipo_doc, ls.reng_num, ls.co_art, ls.co_alma, ls.numero_lote,
               ls.cantidad, ls.fe_us_in
        FROM saLoteSalida ls
        WHERE ls.numero_lote = '3AX2112019'
          AND ls.co_alma = 'P1-PS'
        ORDER BY ls.fe_us_in DESC
    """
    print(sqlcmd(client, sql9))

    client.close()

if __name__ == "__main__":
    run()
