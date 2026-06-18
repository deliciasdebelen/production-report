import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22
TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"

ART_PT = "PT01D01X019"  # artículo con lotes sin costo

def sqlcmd(client, sql, db='carmal_a'):
    clean_sql = " ".join(sql.split()).replace('"', '\\"')
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -Q "{clean_sql}" 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode(errors='replace').strip()

def sqlcmd_file(client, sql, fname, db='carmal_a'):
    sftp = client.open_sftp()
    with sftp.file(fname, 'w') as f: f.write(sql)
    sftp.close()
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm -v /tmp:/tmp mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -i {fname} 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    return stdout.read().decode(errors='replace').strip()

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)

    print("=" * 70)
    print("ANÁLISIS FLUJO: carmal_m (Cierre OP) → carmal_a (AJUS)")
    print("=" * 70)

    # ══════════════════════════════════════════════════════════════════
    # 1. ESTRUCTURA NSPCierreOP en carmal_m
    # ══════════════════════════════════════════════════════════════════
    print("\n═══ [1] COLUMNAS NSPCierreOP (cierre de orden de producción) ═══")
    print(sqlcmd(client, """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'NSPCierreOP'
        ORDER BY ORDINAL_POSITION
    """, 'carmal_m'))

    print("\n═══ [2] COLUMNAS NSPCierreOPReng (renglones del cierre) ═══")
    print(sqlcmd(client, """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'NSPCierreOPReng'
        ORDER BY ORDINAL_POSITION
    """, 'carmal_m'))

    # ══════════════════════════════════════════════════════════════════
    # 2. CIERRES RECIENTES — buscar los que generaron AJUS de PT01D01X019
    # ══════════════════════════════════════════════════════════════════
    print("\n═══ [3] ÚLTIMOS CIERRES OP en carmal_m (últimos 30 días) ═══")
    print(sqlcmd(client, """
        SELECT TOP 20
               c.cierre_num, c.odp_num,
               CONVERT(VARCHAR, c.fecha, 103) AS fecha,
               c.co_art, c.cantidad, c.costo_total, c.costo_unit,
               c.trasnfe, c.revisado,
               CONVERT(VARCHAR, c.fe_us_in, 120) AS creado,
               c.co_us_in
        FROM NSPCierreOP c
        WHERE c.fecha >= DATEADD(DAY, -30, GETDATE())
        ORDER BY c.fecha DESC
    """, 'carmal_m'))

    # ══════════════════════════════════════════════════════════════════
    # 3. BUSCAR CIERRE ESPECÍFICO QUE GENERÓ AJUS DE PT01D01X019
    # ══════════════════════════════════════════════════════════════════
    print(f"\n═══ [4] CIERRES QUE GENERARON {ART_PT} (buscando en NSPCierreOPReng) ═══")
    print(sqlcmd(client, f"""
        SELECT c.cierre_num, c.odp_num,
               CONVERT(VARCHAR, c.fecha, 103) AS fecha_cierre,
               c.co_art AS art_producido,
               c.cantidad AS cant_producida,
               c.costo_total, c.costo_unit,
               r.reng_num, r.co_art AS art_reng,
               r.cantidad AS cant_reng,
               r.costo_unit AS costo_unit_reng,
               r.costo_total AS costo_total_reng
        FROM NSPCierreOP c
        JOIN NSPCierreOPReng r ON r.cierre_num = c.cierre_num
        WHERE (c.co_art = '{ART_PT}'
            OR r.co_art = '{ART_PT}')
          AND c.fecha >= '2026-01-01'
        ORDER BY c.fecha DESC
    """, 'carmal_m'))

    # ══════════════════════════════════════════════════════════════════
    # 4. EL PUENTE: saIntegr (tabla de integración entre sistemas)
    # ══════════════════════════════════════════════════════════════════
    print("\n═══ [5] COLUMNAS saIntegr (puente carmal_m → carmal_a) ═══")
    print(sqlcmd(client, """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'saIntegr'
        ORDER BY ORDINAL_POSITION
    """, 'carmal_a'))

    print("\n═══ [6] ÚLTIMAS INTEGRACIONES en saIntegr ═══")
    print(sqlcmd(client, """
        SELECT TOP 20 *
        FROM saIntegr
        ORDER BY fe_us_in DESC
    """, 'carmal_a'))

    # ══════════════════════════════════════════════════════════════════
    # 5. CÓMO VIAJA EL COSTO: NSPCostocierre en carmal_m
    # ══════════════════════════════════════════════════════════════════
    print("\n═══ [7] COLUMNAS NSPCostocierre (costos calculados del cierre) ═══")
    print(sqlcmd(client, """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'NSPCostocierre'
        ORDER BY ORDINAL_POSITION
    """, 'carmal_m'))

    print("\n═══ [8] MUESTRAS NSPCostocierre — costos últimos cierres ═══")
    print(sqlcmd(client, """
        SELECT TOP 10 cc.cierre_num, cc.co_art, cc.costo_total,
               cc.costo_unit, cc.cantidad,
               CONVERT(VARCHAR, cc.fe_us_in, 120) AS creado
        FROM NSPCostocierre cc
        ORDER BY cc.fe_us_in DESC
    """, 'carmal_m'))

    # ══════════════════════════════════════════════════════════════════
    # 6. TRIGGERS EN carmal_m que envían a carmal_a
    # ══════════════════════════════════════════════════════════════════
    print("\n═══ [9] TRIGGERS EN NSPCierreOP/NSPCierreOPReng ═══")
    print(sqlcmd(client, """
        SELECT t.name AS trigger_name,
               o.name AS tabla,
               CASE WHEN t.is_disabled=0 THEN 'ACTIVO' ELSE 'INACTIVO' END AS estado,
               SUBSTRING(sm.definition, 1, 500) AS fragmento_codigo
        FROM sys.triggers t
        JOIN sys.objects o ON o.object_id = t.parent_id
        JOIN sys.sql_modules sm ON sm.object_id = t.object_id
        WHERE o.name IN ('NSPCierreOP', 'NSPCierreOPReng', 'NSPOrdenproduccion')
    """, 'carmal_m'))

    # ══════════════════════════════════════════════════════════════════
    # 7. STORED PROCEDURES que hacen el trasnfe (traslado de datos)
    # ══════════════════════════════════════════════════════════════════
    print("\n═══ [10] SPs EN carmal_m QUE REFERENCIAN saAjuste / AJUS / costo ═══")
    print(sqlcmd(client, """
        SELECT r.ROUTINE_NAME, r.ROUTINE_TYPE
        FROM INFORMATION_SCHEMA.ROUTINES r
        WHERE (r.ROUTINE_DEFINITION LIKE '%saAjuste%'
            OR r.ROUTINE_DEFINITION LIKE '%AJUS%'
            OR r.ROUTINE_DEFINITION LIKE '%costo_unit%'
            OR r.ROUTINE_DEFINITION LIKE '%carmal_a%'
            OR r.ROUTINE_DEFINITION LIKE '%trasnfe%')
        ORDER BY r.ROUTINE_NAME
    """, 'carmal_m'))

    # ══════════════════════════════════════════════════════════════════
    # 8. NSPCostocierre PARA LOS CIERRES QUE GENERARON LOTES SIN COSTO
    # ══════════════════════════════════════════════════════════════════
    print("\n═══ [11] NSPCostocierre CIERRES DE FECHA 22/05 Y 26/05 ═══")
    print(sqlcmd(client, """
        SELECT cc.cierre_num, cc.co_art, cc.costo_total, cc.costo_unit,
               cc.cantidad, CONVERT(VARCHAR, cc.fe_us_in, 120) AS creado
        FROM NSPCostocierre cc
        WHERE cc.fe_us_in >= '2026-05-19'
        ORDER BY cc.fe_us_in DESC
    """, 'carmal_m'))

    # ══════════════════════════════════════════════════════════════════
    # 9. AJUSTES EN carmal_a — COLUMNAS REALES
    # ══════════════════════════════════════════════════════════════════
    print("\n═══ [12] COLUMNAS saAjuste y saAjusteReng (carmal_a) ═══")
    for t in ['saAjuste', 'saAjusteReng']:
        print(f"\n  {t}:")
        print(sqlcmd(client, f"""
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{t}'
            ORDER BY ORDINAL_POSITION
        """, 'carmal_a'))

    # ══════════════════════════════════════════════════════════════════
    # 10. LOS AJUSTES DE JBARRI CON PRECIO=0 — ¿vienen del sistema?
    # ══════════════════════════════════════════════════════════════════
    print(f"\n═══ [13] AJUSTES (saAjuste) CREADOS POR JBARRI CON fecha 19-26 MAY 2026 ═══")
    print(sqlcmd(client, """
        SELECT a.ajue_num,
               CONVERT(VARCHAR, a.fecha, 103) AS fecha,
               a.co_tipo, a.co_us_in AS usuario,
               CONVERT(VARCHAR, a.fe_us_in, 120) AS creado,
               a.dis_cen
        FROM saAjuste a
        WHERE a.co_us_in = 'JBARRI'
          AND a.fecha >= '2026-05-19'
        ORDER BY a.fecha DESC
    """, 'carmal_a'))

    print(f"\n═══ [14] RENGLONES DE LOS AJUSTES DE JBARRI — ¿qué artículos y qué costo? ═══")
    print(sqlcmd(client, """
        SELECT a.ajue_num,
               CONVERT(VARCHAR, a.fecha, 103) AS fecha,
               ar.co_art, ar.co_alma, ar.co_tipo,
               ar.total_art AS cantidad,
               ar.cost_unit AS costo_unitario,
               ar.lote_asignado
        FROM saAjuste a
        JOIN saAjusteReng ar ON ar.ajue_num = a.ajue_num
        WHERE a.co_us_in = 'JBARRI'
          AND a.fecha >= '2026-05-19'
        ORDER BY a.fecha DESC, ar.reng_num
    """, 'carmal_a'))

    # ══════════════════════════════════════════════════════════════════
    # 11. NSPCostoxArticulo — tabla de costos calculados por Manufact
    # ══════════════════════════════════════════════════════════════════
    print("\n═══ [15] NSPCostoxArticulo (costos por artículo en carmal_m) ═══")
    print(sqlcmd(client, """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'NSPCostoxArticulo'
        ORDER BY ORDINAL_POSITION
    """, 'carmal_m'))
    print(sqlcmd(client, "SELECT * FROM NSPCostoxArticulo", 'carmal_m'))

    # ══════════════════════════════════════════════════════════════════
    # 12. RASTREAR EL CIERRE QUE ORIGINÓ L1 260519-01 y L1 260520-01
    # ══════════════════════════════════════════════════════════════════
    print("\n═══ [16] NSPCierreOP CIERRES DEL 20-22 MAY 2026 ═══")
    print(sqlcmd(client, """
        SELECT c.cierre_num, c.odp_num, c.co_art,
               c.cantidad, c.costo_total, c.costo_unit,
               CONVERT(VARCHAR, c.fecha, 103) AS fecha,
               c.trasnfe,
               CONVERT(VARCHAR, c.fe_us_in, 120) AS creado,
               c.co_us_in
        FROM NSPCierreOP c
        WHERE c.fecha BETWEEN '2026-05-19' AND '2026-05-27'
        ORDER BY c.fecha DESC
    """, 'carmal_m'))

    print("\n═══ [17] NSPCierreOPReng PARA CIERRES DEL 20-22 MAY ═══")
    print(sqlcmd(client, """
        SELECT r.cierre_num, r.reng_num, r.co_art,
               r.cantidad, r.costo_unit, r.costo_total,
               r.num_lote
        FROM NSPCierreOPReng r
        WHERE r.cierre_num IN (
            SELECT cierre_num FROM NSPCierreOP
            WHERE fecha BETWEEN '2026-05-19' AND '2026-05-27'
        )
        ORDER BY r.cierre_num, r.reng_num
    """, 'carmal_m'))

    # ══════════════════════════════════════════════════════════════════
    # 13. NSPLog — log del sistema, errores de integración
    # ══════════════════════════════════════════════════════════════════
    print("\n═══ [18] NSPLog — ÚLTIMAS ENTRADAS (errores de integración) ═══")
    print(sqlcmd(client, """
        SELECT TOP 20 *
        FROM NSPLog
        ORDER BY fe_us_in DESC
    """, 'carmal_m'))

    client.close()

if __name__ == "__main__":
    run()
