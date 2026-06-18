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
    print("ANÁLISIS FINAL - Bug: lotes GCOM no vinculados a generaciones")
    print("=" * 70)

    # El tipo_doc correcto es GCOM (Generación de Compuesto)
    # Las 3 salidas GCOM de mayo tienen Rowguid_Lote pero NO coinciden con renglones

    print("\n[1] TODOS LOS MOVIMIENTOS GCOM EN saLoteSalida (Mayo 2026)")
    sql1 = """
        SELECT tipo_doc, co_art, co_alma, numero_lote, cantidad,
               CONVERT(VARCHAR, fe_us_in, 120) AS fecha,
               CAST(Rowguid_Lote AS VARCHAR(50)) AS Rowguid_Lote
        FROM saLoteSalida
        WHERE tipo_doc = 'GCOM' AND fe_us_in >= '2026-05-01'
        ORDER BY fe_us_in DESC
    """
    print(sqlcmd(client, sql1))

    print("\n[2] CRUZAR ROWGUID_LOTE DE GCOM CON saArtCompuestoGenReng")
    sql2 = """
        SELECT ls.tipo_doc, ls.co_art, ls.co_alma, ls.numero_lote, ls.cantidad,
               CONVERT(VARCHAR, ls.fe_us_in, 120) AS fecha,
               CAST(ls.Rowguid_Lote AS VARCHAR(50)) AS rg_lote,
               r.gene_num, r.reng_num, r.lote_asignado
        FROM saLoteSalida ls
        LEFT JOIN saArtCompuestoGenReng r ON r.rowguid = ls.Rowguid_Lote
        WHERE ls.tipo_doc = 'GCOM' AND ls.fe_us_in >= '2026-05-01'
        ORDER BY ls.fe_us_in DESC
    """
    print(sqlcmd(client, sql2))

    print("\n[3] GENERACIONES DE MAYO 2026 (TODAS)")
    sql3 = """
        SELECT gene_num, co_art, co_alma,
               CONVERT(VARCHAR, fecha, 103) AS fecha,
               total_art, gene_art,
               CASE WHEN gene_art = 1 THEN 'CERRADA' ELSE '*** ABIERTA ***' END AS estado
        FROM saArtCompuestoGen
        WHERE fecha >= '2026-05-01'
        ORDER BY fecha DESC, gene_num DESC
    """
    print(sqlcmd(client, sql3))

    print("\n[4] RENGLONES GEN 0000000949 - buscar por gene_num exacto")
    sql4 = "SELECT * FROM saArtCompuestoGenReng WHERE gene_num = '0000000949'"
    print(sqlcmd(client, sql4))

    print("\n[5] RENGLONES DE LAS 5 ÚLTIMAS GENERACIONES ABIERTAS DE MAYO")
    sql5 = """
        SELECT r.gene_num, r.reng_num, r.co_art, r.co_alma, r.total_art, r.lote_asignado,
               g.fecha, g.gene_art
        FROM saArtCompuestoGenReng r
        JOIN saArtCompuestoGen g ON g.gene_num = r.gene_num
        WHERE g.fecha >= '2026-05-01' AND g.gene_art = 0
        ORDER BY g.fecha DESC, r.gene_num, r.reng_num
    """
    print(sqlcmd(client, sql5))

    print("\n[6] VERIFICAR ESTRUCTURA: ¿saLoteSalida.reng_num coincide con renglón de la gen?")
    # Si el vínculo es por reng_num y tipo_doc en lugar de rowguid
    sql6 = """
        SELECT ls.tipo_doc, ls.reng_num, ls.co_art, ls.co_alma, ls.numero_lote, ls.cantidad,
               CONVERT(VARCHAR, ls.fe_us_in, 120) AS fecha,
               r.gene_num, r.lote_asignado
        FROM saLoteSalida ls
        LEFT JOIN saArtCompuestoGenReng r 
            ON r.reng_num = ls.reng_num AND r.co_art = ls.co_art
        WHERE ls.tipo_doc = 'GCOM' AND ls.fe_us_in >= '2026-05-01'
        ORDER BY ls.fe_us_in DESC
    """
    print(sqlcmd(client, sql6))

    print("\n[7] PATRÓN COMPLETO: Generaciones CERRADAS con saLoteSalida asociado")
    sql7 = """
        SELECT TOP 10
            r.gene_num, r.reng_num, r.co_art, r.lote_asignado,
            ls.numero_lote, ls.cantidad AS cant_salida,
            ls.tipo_doc,
            CONVERT(VARCHAR, ls.fe_us_in, 120) AS fecha_salida
        FROM saArtCompuestoGenReng r
        JOIN saArtCompuestoGen g ON g.gene_num = r.gene_num AND g.gene_art = 1
        JOIN saLoteSalida ls ON ls.Rowguid_Lote = r.rowguid
        WHERE g.fecha >= '2026-01-01'
        ORDER BY g.fecha DESC
    """
    print(sqlcmd(client, sql7))

    print("\n[8] TRIGGER/SP: ¿Existe trigger en saArtCompuestoGenReng o saArtCompuestoGen?")
    sql8 = """
        SELECT t.name AS trigger_name, o.name AS table_name, t.is_disabled
        FROM sys.triggers t
        JOIN sys.objects o ON o.object_id = t.parent_id
        WHERE o.name IN ('saArtCompuestoGen', 'saArtCompuestoGenReng', 'saLoteEntrada', 'saLoteSalida')
        ORDER BY o.name
    """
    print(sqlcmd(client, sql8))

    client.close()

if __name__ == "__main__":
    run()
