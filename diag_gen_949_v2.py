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
    print("BÚSQUEDA AMPLIADA - Generación 0000000949")
    print("=" * 70)

    # La gen 949 no aparece en saArtCompuestoGen con co_art D17 ni COMP32
    # Busquemos el número 949 en todas las tablas posibles

    print("\n[A] BUSCAR gene_num '0000000949' SIN FILTRO de co_art")
    sql_a = "SELECT gene_num, co_art, co_alma, CONVERT(VARCHAR,fecha,103) AS fecha, total_art, gene_art FROM saArtCompuestoGen WHERE gene_num = '0000000949'"
    print(sqlcmd(client, sql_a))

    print("\n[B] ÚLTIMAS 20 GENERACIONES DE CUALQUIER ARTÍCULO (sin filtro)")
    sql_b = """
        SELECT TOP 20 gene_num, co_art, co_alma, 
               CONVERT(VARCHAR,fecha,103) AS fecha, total_art, gene_art,
               CASE WHEN gene_art = 1 THEN 'CERRADA' ELSE 'ABIERTA' END AS estado
        FROM saArtCompuestoGen
        ORDER BY gene_num DESC
    """
    print(sqlcmd(client, sql_b))

    print("\n[C] GENERACIONES EN MAYO 2026 CON gene_art = 0 (ABIERTAS/PROBLEMÁTICAS)")
    sql_c = """
        SELECT gene_num, co_art, co_alma, 
               CONVERT(VARCHAR,fecha,103) AS fecha, total_art, gene_art,
               CASE WHEN gene_art = 1 THEN 'CERRADA' ELSE '*** ABIERTA ***' END AS estado
        FROM saArtCompuestoGen
        WHERE fecha >= '2026-05-01'
        ORDER BY fecha DESC, gene_num DESC
    """
    print(sqlcmd(client, sql_c))

    print("\n[D] GENERACIONES ABIERTAS (gene_art=0) EN TODOS LOS TIEMPOS")
    sql_d = """
        SELECT TOP 30 gene_num, co_art, co_alma,
               CONVERT(VARCHAR,fecha,103) AS fecha, total_art,
               CONVERT(VARCHAR,fe_us_mo,120) AS ultima_mod
        FROM saArtCompuestoGen
        WHERE gene_art = 0
        ORDER BY fecha DESC, gene_num DESC
    """
    print(sqlcmd(client, sql_d))

    print("\n[E] VERIFICAR: ¿Existe gen 949 en stgFactLoteGen o similar?")
    sql_e = """
        SELECT TOP 10 * FROM stgFactLoteGen ORDER BY 1 DESC
    """
    print(sqlcmd(client, sql_e))

    print("\n[F] COLUMNAS DE stgFactLoteGen")
    sql_f = "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'stgFactLoteGen' ORDER BY ORDINAL_POSITION"
    print(sqlcmd(client, sql_f))

    # Analizar el patrón de renglones sin lotes consumidos en generaciones cerradas
    print("\n[G] GENERACIONES CERRADAS CON RENGLONES SIN LOTE ASIGNADO (bug pattern)")
    sql_g = """
        SELECT TOP 20 
            r.gene_num, r.reng_num, r.co_art, r.lote_asignado,
            g.fecha, g.gene_art,
            ls.numero_lote, ls.cantidad AS cant_consumida
        FROM saArtCompuestoGenReng r
        JOIN saArtCompuestoGen g ON g.gene_num = r.gene_num
        LEFT JOIN saLoteSalida ls ON ls.Rowguid_Lote = r.rowguid
        WHERE g.gene_art = 1
          AND r.lote_asignado = 0
          AND g.fecha >= '2026-01-01'
        ORDER BY g.fecha DESC, r.gene_num DESC
    """
    print(sqlcmd(client, sql_g))

    # Analizar la generación 882 que aparecía con gene_art=1 pero lote_asignado=0
    print("\n[H] ANÁLISIS GENERACIÓN 0000000882 (cerrada pero sin lotes en saLoteSalida)")
    sql_h = """
        SELECT r.gene_num, r.reng_num, r.co_art, r.co_alma, r.total_art, r.lote_asignado,
               ls.numero_lote, ls.cantidad, ls.tipo_doc,
               CONVERT(VARCHAR, ls.fe_us_in, 120) AS ls_fecha
        FROM saArtCompuestoGenReng r
        LEFT JOIN saLoteSalida ls ON ls.Rowguid_Lote = r.rowguid
        WHERE r.gene_num = '0000000882'
        ORDER BY r.reng_num
    """
    print(sqlcmd(client, sql_h))

    # Ver si las generaciones exitosas previas tienen saLoteSalida con tipo_doc diferente
    print("\n[I] MOVIMIENTOS saLoteSalida MAYO 2026 (todos los tipos_doc)")
    sql_i = """
        SELECT DISTINCT tipo_doc, COUNT(*) AS cantidad, 
               MIN(CONVERT(VARCHAR, fe_us_in, 120)) AS primera,
               MAX(CONVERT(VARCHAR, fe_us_in, 120)) AS ultima
        FROM saLoteSalida
        WHERE fe_us_in >= '2026-05-01'
        GROUP BY tipo_doc
        ORDER BY ultima DESC
    """
    print(sqlcmd(client, sql_i))

    print("\n[J] saLoteSalida MAYO 2026 para MP04N00X021 (Ácido Cítrico)")
    sql_j = """
        SELECT tipo_doc, co_art, co_alma, numero_lote, cantidad,
               CONVERT(VARCHAR, fe_us_in, 120) AS fecha,
               CAST(Rowguid_Lote AS VARCHAR(50)) AS rg_lote
        FROM saLoteSalida
        WHERE fe_us_in >= '2026-05-01'
          AND co_art = 'MP04N00X021'
        ORDER BY fe_us_in DESC
    """
    print(sqlcmd(client, sql_j))

    client.close()

if __name__ == "__main__":
    run()
