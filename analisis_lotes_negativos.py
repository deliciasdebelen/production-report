import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22
TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"

# Artículos con lotes negativos visibles en la imagen
ARTS_NEGATIVOS = [
    'PT01D01X011',  # Mayonesa Premium Trad PET 3.3 Kg  - L2 260302-02  -60,000
    'PT01D01X019',  # Mayonesa Premium Trad PET 445g    - L1 260302-01  -48,000
    'PT01P01X011',  # Mayonesa Trad PEAD 3.3 kg         - ME260312-03   -4,000
    'PT01P01X059',  # Mayonesa Trad PEAD 445g           - L1 260227-01  -11,000
    'PT01P01X013',  # Mayonesa Trad PEAD 175g           - varios lotes  -576,000
    'PT01P01X017',  # Mayonesa Trad PEAD Sqeeze 200g    - L1 260211-01  -480,000
    'PT04D16X001',  # Mermelada Varietal Fresa 250g     - AFR260224-01  -2,000
]
ALMA = 'P1-PT'

def sqlcmd(client, sql, db='carmal_a'):
    clean_sql = " ".join(sql.split()).replace('"', '\\"')
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -Q "{clean_sql}" 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=40)
    return stdout.read().decode(errors='replace').strip()

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)

    arts_str = "','".join(ARTS_NEGATIVOS)

    print("=" * 70)
    print("ANÁLISIS: LOTES CON STOCK NEGATIVO EN P1-PT — carmal_a")
    print("=" * 70)

    # ══════════════════════════════════════════════════════════════════
    # SECCIÓN 1 — DIAGRAMA BD: TABLAS CLAVE carmal_a
    # ══════════════════════════════════════════════════════════════════
    print("\n═══ [BD-1] TABLAS PRINCIPALES carmal_a (inventario/ventas/lotes) ═══")
    sql_tabs = """
        SELECT t.name AS tabla, p.rows AS filas
        FROM sys.tables t
        JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id <= 1
        WHERE t.name LIKE 'sa%'
           OR t.name LIKE 'st%'
        ORDER BY p.rows DESC
    """
    print(sqlcmd(client, sql_tabs))

    # ══════════════════════════════════════════════════════════════════
    # SECCIÓN 2 — COLUMNAS CLAVE DE TABLAS DE LOTES
    # ══════════════════════════════════════════════════════════════════
    print("\n═══ [BD-2] COLUMNAS saLoteEntrada ═══")
    print(sqlcmd(client, """
        SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'saLoteEntrada' ORDER BY ORDINAL_POSITION
    """))

    print("\n═══ [BD-3] COLUMNAS saLoteSalida ═══")
    print(sqlcmd(client, """
        SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'saLoteSalida' ORDER BY ORDINAL_POSITION
    """))

    print("\n═══ [BD-4] COLUMNAS saStockAlmacen ═══")
    print(sqlcmd(client, """
        SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'saStockAlmacen' ORDER BY ORDINAL_POSITION
    """))

    # ══════════════════════════════════════════════════════════════════
    # SECCIÓN 3 — DIAGNÓSTICO LOTES NEGATIVOS EN P1-PT
    # ══════════════════════════════════════════════════════════════════
    print(f"\n═══ [DIAG-1] TODOS LOS LOTES CON stock_actual < 0 EN P1-PT ═══")
    sql_neg = f"""
        SELECT le.co_art, a.art_des,
               le.numero_lote,
               CONVERT(VARCHAR, le.fecha_inicio, 103)     AS FecIni,
               CONVERT(VARCHAR, le.fecha_expiracion, 103) AS FecExp,
               le.co_alma,
               le.cantidad     AS cant_entrada,
               le.stock_actual,
               (le.cantidad - le.stock_actual) AS total_salidas_implicadas
        FROM saLoteEntrada le
        JOIN saArticulo a ON a.co_art = le.co_art
        WHERE le.co_alma = '{ALMA}'
          AND le.stock_actual < 0
        ORDER BY le.stock_actual ASC
    """
    print(sqlcmd(client, sql_neg))

    print(f"\n═══ [DIAG-2] RESUMEN IMPACTO POR ARTÍCULO ═══")
    sql_res = f"""
        SELECT le.co_art, a.art_des,
               COUNT(DISTINCT le.numero_lote) AS num_lotes_negativos,
               SUM(le.stock_actual) AS stock_total_negativo,
               SUM(le.cantidad) AS total_entradas,
               SUM(le.cantidad - le.stock_actual) AS total_salidas_aplicadas
        FROM saLoteEntrada le
        JOIN saArticulo a ON a.co_art = le.co_art
        WHERE le.co_alma = '{ALMA}'
          AND le.stock_actual < 0
        GROUP BY le.co_art, a.art_des
        ORDER BY SUM(le.stock_actual) ASC
    """
    print(sqlcmd(client, sql_res))

    # ══════════════════════════════════════════════════════════════════
    # SECCIÓN 4 — MOVIMIENTOS QUE GENERARON EL NEGATIVO
    # ══════════════════════════════════════════════════════════════════
    print(f"\n═══ [DIAG-3] TIPOS DE DOCUMENTO EN saLoteSalida PARA LOTES NEGATIVOS ═══")
    sql_tipos = f"""
        SELECT ls.tipo_doc,
               COUNT(*) AS movimientos,
               SUM(ls.cantidad) AS total_cantidad,
               MIN(CONVERT(VARCHAR, ls.fe_us_in, 103)) AS fecha_min,
               MAX(CONVERT(VARCHAR, ls.fe_us_in, 103)) AS fecha_max
        FROM saLoteSalida ls
        JOIN saLoteEntrada le ON le.numero_lote = ls.numero_lote
                              AND le.co_art = ls.co_art
                              AND le.co_alma = ls.co_alma
        WHERE le.co_alma = '{ALMA}'
          AND le.stock_actual < 0
          AND ls.co_alma = '{ALMA}'
        GROUP BY ls.tipo_doc
        ORDER BY SUM(ls.cantidad) DESC
    """
    print(sqlcmd(client, sql_tipos))

    # ══════════════════════════════════════════════════════════════════
    # SECCIÓN 5 — DETALLE DE MOVIMIENTOS DEL LOTE MÁS NEGATIVO
    # ══════════════════════════════════════════════════════════════════
    # PT01P01X013 / L1 260219-01  -576,000 (el mayor en la imagen)
    print(f"\n═══ [DIAG-4] HISTORIAL COMPLETO LOTE PT01P01X013 / L1 260219-01 ═══")
    sql_hist1 = """
        SELECT 'ENTRADA' AS mov, le.numero_lote, le.co_alma,
               le.cantidad, le.stock_actual,
               CONVERT(VARCHAR, le.fecha_inicio, 103) AS FecIni,
               CONVERT(VARCHAR, le.fecha_expiracion, 103) AS FecExp,
               le.rowguid_reng
        FROM saLoteEntrada le
        WHERE le.co_art = 'PT01P01X013' AND le.numero_lote = 'L1 260219-01'
          AND le.co_alma = 'P1-PT'
    """
    print(sqlcmd(client, sql_hist1))

    sql_hist2 = """
        SELECT ls.tipo_doc, ls.numero_lote, ls.co_alma, ls.cantidad,
               CONVERT(VARCHAR, ls.fe_us_in, 120) AS fecha,
               ls.co_us_in AS usuario
        FROM saLoteSalida ls
        WHERE ls.co_art = 'PT01P01X013' AND ls.numero_lote = 'L1 260219-01'
          AND ls.co_alma = 'P1-PT'
        ORDER BY ls.fe_us_in ASC
    """
    print(sqlcmd(client, sql_hist2))

    # Segundo lote más negativo: PT01P01X017 / L1 260211-01 -480,000
    print(f"\n═══ [DIAG-5] HISTORIAL PT01P01X017 / L1 260211-01 (-480,000) ═══")
    sql_hist3 = """
        SELECT 'ENTRADA' AS tipo, le.numero_lote, le.cantidad AS cant_entrada,
               le.stock_actual,
               CONVERT(VARCHAR, le.fecha_inicio, 103) AS FecIni,
               CONVERT(VARCHAR, le.fecha_expiracion, 103) AS FecExp
        FROM saLoteEntrada le
        WHERE le.co_art = 'PT01P01X017' AND le.numero_lote = 'L1 260211-01'
          AND le.co_alma = 'P1-PT'
    """
    print(sqlcmd(client, sql_hist3))

    sql_hist4 = """
        SELECT ls.tipo_doc, SUM(ls.cantidad) AS total_salida, COUNT(*) AS movs,
               MIN(CONVERT(VARCHAR, ls.fe_us_in, 103)) AS desde,
               MAX(CONVERT(VARCHAR, ls.fe_us_in, 103)) AS hasta
        FROM saLoteSalida ls
        WHERE ls.co_art = 'PT01P01X017' AND ls.numero_lote = 'L1 260211-01'
          AND ls.co_alma = 'P1-PT'
        GROUP BY ls.tipo_doc
        ORDER BY total_salida DESC
    """
    print(sqlcmd(client, sql_hist4))

    # ══════════════════════════════════════════════════════════════════
    # SECCIÓN 6 — FACTURAS EMITIDAS CON ESOS LOTES (tipo_doc = FACT/NOTA)
    # ══════════════════════════════════════════════════════════════════
    print(f"\n═══ [DIAG-6] FACTURAS EMITIDAS CON LOTES NEGATIVOS (últimos 90 días) ═══")
    sql_fact = f"""
        SELECT ls.tipo_doc, ls.co_art, a.art_des,
               ls.numero_lote, SUM(ls.cantidad) AS cant_facturada,
               COUNT(*) AS num_movimientos,
               MIN(CONVERT(VARCHAR, ls.fe_us_in, 103)) AS primera,
               MAX(CONVERT(VARCHAR, ls.fe_us_in, 103)) AS ultima
        FROM saLoteSalida ls
        JOIN saArticulo a ON a.co_art = ls.co_art
        JOIN saLoteEntrada le ON le.numero_lote = ls.numero_lote
                              AND le.co_art = ls.co_art
                              AND le.co_alma = ls.co_alma
        WHERE ls.co_alma = '{ALMA}'
          AND le.stock_actual < 0
          AND ls.fe_us_in >= DATEADD(DAY, -90, GETDATE())
          AND ls.tipo_doc IN ('FACT', 'NOTA', 'FAC', 'NE')
        GROUP BY ls.tipo_doc, ls.co_art, a.art_des, ls.numero_lote
        ORDER BY SUM(ls.cantidad) DESC
    """
    print(sqlcmd(client, sql_fact))

    # ══════════════════════════════════════════════════════════════════
    # SECCIÓN 7 — TIPOS DE DOCUMENTO DISTINTOS EN saLoteSalida
    # ══════════════════════════════════════════════════════════════════
    print(f"\n═══ [DIAG-7] TIPOS DE DOCUMENTO DISTINTOS EN saLoteSalida ═══")
    print(sqlcmd(client, """
        SELECT tipo_doc, COUNT(*) AS movimientos, SUM(cantidad) AS total
        FROM saLoteSalida
        GROUP BY tipo_doc ORDER BY COUNT(*) DESC
    """))

    # ══════════════════════════════════════════════════════════════════
    # SECCIÓN 8 — PARÁMETROS DE EMPRESA (lotes negativos)
    # ══════════════════════════════════════════════════════════════════
    print(f"\n═══ [DIAG-8] PARÁMETROS EMPRESA — configuración de lotes ═══")
    # Buscar en saParEmpresa o similar
    for tabla in ['saParEmpresa', 'saParametros', 'saConfiguracion', 'saParVenta']:
        cols = sqlcmd(client, f"""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{tabla}' ORDER BY ORDINAL_POSITION
        """)
        if '0 rows' not in cols and cols.strip():
            print(f"\n  Tabla {tabla} existe:")
            data = sqlcmd(client, f"SELECT * FROM {tabla}")
            print(data[:2000])

    # ══════════════════════════════════════════════════════════════════
    # SECCIÓN 9 — ENTRADAS FALTANTES (¿por qué hay más salidas que entradas?)
    # ══════════════════════════════════════════════════════════════════
    print(f"\n═══ [DIAG-9] BALANCE ENTRADA vs SALIDA POR LOTE NEGATIVO ═══")
    sql_balance = f"""
        SELECT le.co_art, a.art_des, le.numero_lote, le.co_alma,
               le.cantidad AS cant_entrada,
               ISNULL((SELECT SUM(ls.cantidad) FROM saLoteSalida ls
                       WHERE ls.co_art = le.co_art
                         AND ls.numero_lote = le.numero_lote
                         AND ls.co_alma = le.co_alma), 0) AS total_salidas,
               le.stock_actual,
               le.cantidad - ISNULL((SELECT SUM(ls.cantidad) FROM saLoteSalida ls
                       WHERE ls.co_art = le.co_art
                         AND ls.numero_lote = le.numero_lote
                         AND ls.co_alma = le.co_alma), 0) AS balance_calculado,
               CASE WHEN ABS(le.stock_actual -
                    (le.cantidad - ISNULL((SELECT SUM(ls.cantidad) FROM saLoteSalida ls
                       WHERE ls.co_art = le.co_art
                         AND ls.numero_lote = le.numero_lote
                         AND ls.co_alma = le.co_alma), 0))) < 0.01
                    THEN 'CONSISTENTE'
                    ELSE '*** INCONSISTENTE ***' END AS consistencia
        FROM saLoteEntrada le
        JOIN saArticulo a ON a.co_art = le.co_art
        WHERE le.co_alma = '{ALMA}'
          AND le.stock_actual < 0
        ORDER BY le.stock_actual ASC
    """
    print(sqlcmd(client, sql_balance))

    # ══════════════════════════════════════════════════════════════════
    # SECCIÓN 10 — ENTRADAS DE LOTE PT01P01X013 COMPARADAS
    # ══════════════════════════════════════════════════════════════════
    print(f"\n═══ [DIAG-10] TODAS LAS ENTRADAS PT01P01X013 EN P1-PT (cualquier lote) ═══")
    sql_ent = """
        SELECT le.numero_lote, le.cantidad, le.stock_actual,
               CONVERT(VARCHAR, le.fecha_inicio, 103) AS FecIni,
               CONVERT(VARCHAR, le.fecha_expiracion, 103) AS FecExp,
               le.rowguid_reng
        FROM saLoteEntrada le
        WHERE le.co_art = 'PT01P01X013' AND le.co_alma = 'P1-PT'
        ORDER BY le.fecha_inicio ASC
    """
    print(sqlcmd(client, sql_ent))

    # ══════════════════════════════════════════════════════════════════
    # SECCIÓN 11 — ¿Hay ajustes de inventario o traslados como fuente?
    # ══════════════════════════════════════════════════════════════════
    print(f"\n═══ [DIAG-11] TIPOS DE ENTRADA EN saLoteEntrada ═══")
    print(sqlcmd(client, """
        SELECT tipo_doc, COUNT(*) AS movimientos, SUM(cantidad) AS total
        FROM saLoteEntrada
        GROUP BY tipo_doc ORDER BY COUNT(*) DESC
    """))

    # Buscar columna tipo_doc en saLoteEntrada
    print(f"\n═══ [DIAG-12] ENTRADAS POR TIPO para artículos negativos ═══")
    sql_ent_tipo = f"""
        SELECT le.tipo_doc, le.co_art, le.numero_lote,
               le.cantidad, le.stock_actual,
               CONVERT(VARCHAR, le.fecha_inicio, 103) AS FecIni
        FROM saLoteEntrada le
        WHERE le.co_art IN ('{arts_str}')
          AND le.co_alma = '{ALMA}'
          AND le.stock_actual < 0
        ORDER BY le.co_art, le.fecha_inicio
    """
    print(sqlcmd(client, sql_ent_tipo))

    # ══════════════════════════════════════════════════════════════════
    # SECCIÓN 12 — TRIGGER trg_BlockLoteSinExistencia análisis
    # ══════════════════════════════════════════════════════════════════
    print(f"\n═══ [DIAG-13] TRIGGERS en saLoteSalida (activos) ═══")
    print(sqlcmd(client, """
        SELECT t.name, CASE WHEN t.is_disabled=0 THEN 'ACTIVO' ELSE 'INACTIVO' END AS estado,
               OBJECT_DEFINITION(t.object_id) AS codigo
        FROM sys.triggers t
        JOIN sys.objects o ON o.object_id = t.parent_id
        WHERE o.name = 'saLoteSalida'
    """))

    # ══════════════════════════════════════════════════════════════════
    # SECCIÓN 13 — STOCK TOTAL DEL ALMACÉN P1-PT para PT01P01X013
    # ══════════════════════════════════════════════════════════════════
    print(f"\n═══ [DIAG-14] STOCK TOTAL saStockAlmacen para artículos negativos ═══")
    sql_stock = f"""
        SELECT sa.co_art, a.art_des, sa.co_alma, sa.tipo, sa.stock
        FROM saStockAlmacen sa
        JOIN saArticulo a ON a.co_art = sa.co_art
        WHERE sa.co_art IN ('{arts_str}')
          AND sa.co_alma = '{ALMA}'
        ORDER BY sa.co_art, sa.tipo
    """
    print(sqlcmd(client, sql_stock))

    client.close()

if __name__ == "__main__":
    run()
