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
    print("DIAGNÓSTICO: Compuesto 32 (gene_num=0000000946)")
    print("=" * 70)

    # 1. Generación de compuesto 0000000946
    print("\n[1] GENERACIÓN DE COMPUESTO 0000000946 (saArtCompuestoGen)")
    sql = """
        SELECT gene_num, co_art, co_alma, fecha, total_art, gene_art, co_us_in, fe_us_in
        FROM saArtCompuestoGen
        WHERE gene_num = '0000000946'
    """
    print(sqlcmd(client, sql))

    # 2. Renglones de la generación (ingredientes)
    print("\n[2] RENGLONES (INGREDIENTES) DE LA GENERACIÓN 0000000946")
    sql2 = """
        SELECT gene_num, reng_num, co_art, co_alma, co_uni, total_art, lote_asignado, stotal_art
        FROM saArtCompuestoGenReng
        WHERE gene_num = '0000000946'
        ORDER BY reng_num
    """
    print(sqlcmd(client, sql2))

    # 3. Lotes de ACIDO CITRICO (MP04N00X021) - todos con stock
    print("\n[3] LOTES DE ÁCIDO CÍTRICO (MP04N00X021) CON stock_actual > 0")
    sql3 = """
        SELECT numero_lote, co_art, co_alma,
               CONVERT(VARCHAR, fecha_inicio, 103) AS FecIni,
               CONVERT(VARCHAR, fecha_expiracion, 103) AS FecExp,
               cantidad, stock_actual,
               CASE WHEN fecha_expiracion < GETDATE() THEN 'VENCIDO' ELSE 'VIGENTE' END AS EstVenc
        FROM saLoteEntrada
        WHERE co_art = 'MP04N00X021'
          AND stock_actual > 0
        ORDER BY co_alma, fecha_expiracion DESC
    """
    print(sqlcmd(client, sql3))

    # 4. Lote específico 3AX2112019
    print("\n[4] LOTE ESPECÍFICO 3AX2112019")
    sql4 = """
        SELECT numero_lote, co_art, co_alma,
               CONVERT(VARCHAR, fecha_inicio, 103) AS FecIni,
               CONVERT(VARCHAR, fecha_expiracion, 103) AS FecExp,
               cantidad, stock_actual,
               CASE WHEN fecha_expiracion < GETDATE() THEN '*** VENCIDO ***' ELSE 'VIGENTE' END AS EstVenc
        FROM saLoteEntrada
        WHERE numero_lote = '3AX2112019'
    """
    print(sqlcmd(client, sql4))

    # 5. Stock de ACIDO CITRICO en saStockAlmacen
    print("\n[5] STOCK ÁCIDO CÍTRICO POR ALMACÉN (saStockAlmacen)")
    sql5 = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'saStockAlmacen' ORDER BY ORDINAL_POSITION"
    cols = sqlcmd(client, sql5)
    print("Columnas:", cols[:300])

    sql5b = """
        SELECT TOP 5 * FROM saStockAlmacen WHERE co_art = 'MP04N00X021'
    """
    print(sqlcmd(client, sql5b))

    # 6. Lotes en saLoteSalida para esta generación
    print("\n[6] LOTES SALIDA ASOCIADOS A RENGLONES DE LA GEN 0000000946")
    # saLoteSalida tiene: tipo_doc, reng_num, co_art, numero_lote, cantidad
    # Need to find what tipo_doc is for compuesto gen - might be 'GC' or similar
    sql6 = """
        SELECT ls.tipo_doc, ls.reng_num, ls.co_art, ls.co_alma, ls.numero_lote,
               ls.cantidad,
               CONVERT(VARCHAR, le.fecha_expiracion, 103) AS FecExp,
               CASE WHEN le.fecha_expiracion < GETDATE() THEN '*** VENCIDO ***' ELSE 'VIGENTE' END AS EstVenc
        FROM saLoteSalida ls
        LEFT JOIN saLoteEntrada le ON le.numero_lote = ls.numero_lote AND le.co_art = ls.co_art
        WHERE ls.rowguid_reng IN (
            SELECT rowguid FROM saArtCompuestoGenReng WHERE gene_num = '0000000946'
        )
    """
    print(sqlcmd(client, sql6))

    # 7. Buscar las generaciones recientes de Compuesto 32
    print("\n[7] ÚLTIMAS GENERACIONES DEL ARTÍCULO COMPUESTO 32")
    sql7 = """
        SELECT TOP 10 gene_num, co_art, co_alma, 
               CONVERT(VARCHAR,fecha,103) AS Fecha,
               total_art, gene_art
        FROM saArtCompuestoGen
        WHERE co_art LIKE '%D17%' OR co_art = 'MP01D17X0...' OR co_art LIKE '%COMP%32%'
        ORDER BY fecha DESC
    """
    print(sqlcmd(client, sql7))

    # 8. Descubrir cod del compuesto 32
    print("\n[8] CÓDIGO DEL ARTÍCULO COMPUESTO 32 EN saArticulo")
    sql8 = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'saArticulo' ORDER BY ORDINAL_POSITION"
    cols2 = sqlcmd(client, sql8)
    print("Columnas saArticulo:", cols2[:400])

    client.close()

if __name__ == "__main__":
    run()
