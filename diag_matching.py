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
    print("DIAGNÓSTICO: ¿Por qué el SP no encuentra matches?")
    print("=" * 70)

    # 1. Ver los GCOMs huérfanos con su fecha exacta
    print("\n[1] GCOMs huérfanos con fechas exactas")
    sql1 = """
        SELECT ls.co_art, ls.co_alma, ls.numero_lote, ls.cantidad,
               CONVERT(VARCHAR, ls.fe_us_in, 120) AS fecha_gcom
        FROM saLoteSalida ls
        WHERE ls.tipo_doc = 'GCOM'
          AND ls.fe_us_in >= '2026-01-01'
          AND NOT EXISTS (
              SELECT 1 FROM saArtCompuestoGenReng r 
              WHERE r.rowguid = ls.Rowguid_Lote
          )
        ORDER BY ls.fe_us_in DESC
    """
    print(sqlcmd(client, sql1))

    # 2. Buscar renglones que podrían matchear GCOM del 21/05/2026 - SIN filtro lote_asignado
    print("\n[2] Renglones candidatos para MP04N00X021 el 21/05/2026 (sin filtro lote_asignado)")
    sql2 = """
        SELECT r.gene_num, r.reng_num, r.co_art, r.co_alma, r.total_art, r.lote_asignado,
               CONVERT(VARCHAR, g.fecha, 120) AS fecha_gen,
               DATEDIFF(DAY, g.fecha, '2026-05-21') AS diff_dias
        FROM saArtCompuestoGenReng r
        JOIN saArtCompuestoGen g ON g.gene_num = r.gene_num
        WHERE r.co_art = 'MP04N00X021'
          AND r.co_alma = 'P1-PS'
          AND ABS(r.total_art - 0.20) < 0.05
          AND DATEDIFF(DAY, g.fecha, '2026-05-21') BETWEEN -3 AND 3
        ORDER BY g.fecha DESC
    """
    print(sqlcmd(client, sql2))

    # 3. Buscar renglones que podrían matchear GCOM del 22/05/2026
    print("\n[3] Renglones candidatos para MP04N00X021 el 22/05/2026 (sin filtro lote_asignado)")
    sql3 = """
        SELECT r.gene_num, r.reng_num, r.co_art, r.co_alma, r.total_art, r.lote_asignado,
               CONVERT(VARCHAR, g.fecha, 120) AS fecha_gen,
               DATEDIFF(DAY, g.fecha, '2026-05-22') AS diff_dias
        FROM saArtCompuestoGenReng r
        JOIN saArtCompuestoGen g ON g.gene_num = r.gene_num
        WHERE r.co_art = 'MP04N00X021'
          AND r.co_alma = 'P1-PS'
          AND ABS(r.total_art - 0.20) < 0.05
          AND DATEDIFF(DAY, g.fecha, '2026-05-22') BETWEEN -3 AND 3
        ORDER BY g.fecha DESC
    """
    print(sqlcmd(client, sql3))

    # 4. Ver todas las generaciones de mayo que tienen renglón para MP04N00X021
    print("\n[4] Generaciones MAYO 2026 con renglón para Ácido Cítrico")
    sql4 = """
        SELECT g.gene_num, g.gene_art, CONVERT(VARCHAR, g.fecha, 103) AS fecha,
               r.reng_num, r.co_art, r.total_art, r.lote_asignado
        FROM saArtCompuestoGen g
        JOIN saArtCompuestoGenReng r ON r.gene_num = g.gene_num
        WHERE g.fecha >= '2026-05-01'
          AND r.co_art = 'MP04N00X021'
        ORDER BY g.fecha DESC, g.gene_num DESC
    """
    print(sqlcmd(client, sql4))

    # 5. ¿Los GCOMs de hoy son de gen 946 o 949?
    print("\n[5] Contexto: qué generaciones estaban activas el 21-22 de mayo")
    sql5 = """
        SELECT gene_num, co_art, co_alma, 
               CONVERT(VARCHAR, fecha, 103) AS fecha,
               gene_art,
               CASE WHEN gene_art = 0 THEN 'ABIERTA' ELSE 'CERRADA' END AS estado
        FROM saArtCompuestoGen
        WHERE CAST(fecha AS DATE) BETWEEN '2026-05-19' AND '2026-05-22'
        ORDER BY fecha DESC, gene_num DESC
    """
    print(sqlcmd(client, sql5))

    # 6. Analizar el GCOM del 22/05 08:46 - ¿a qué generación corresponde?
    print("\n[6] Análisis del GCOM más reciente (MP04N00X021, 22/05 08:46)")
    sql6 = """
        -- El GCOM registra 0.20 kg para MP04N00X021 en P1-PS el 22/05
        -- Buscar generación cuya total_art para ese artículo sea 0.20 ± 0.05
        -- Buscar también con total_art diferente (podría ser fracción)
        SELECT r.gene_num, r.reng_num, r.co_art, r.total_art, r.lote_asignado,
               g.gene_art, CONVERT(VARCHAR, g.fecha, 103) AS fecha_gen,
               ABS(r.total_art - 0.20) AS diferencia
        FROM saArtCompuestoGenReng r
        JOIN saArtCompuestoGen g ON g.gene_num = r.gene_num
        WHERE r.co_art = 'MP04N00X021'
          AND r.co_alma = 'P1-PS'
          AND g.fecha >= '2026-05-01'
        ORDER BY g.fecha DESC, ABS(r.total_art - 0.20)
    """
    print(sqlcmd(client, sql6))

    client.close()

if __name__ == "__main__":
    run()
