import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22
TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"

ORDEN = "0000009234"

def sqlcmd(client, sql, db='carmal_m'):
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
    print("ANÁLISIS BD: carmal_m vs carmal_a + Error Orden 0000009234")
    print("=" * 70)

    # ─── A. ESQUEMA carmal_m — tablas relevantes manufactura ──────────────
    print("\n═══ A. TABLAS PRINCIPALES EN carmal_m ═══")
    sql_tabs_m = """
        SELECT TABLE_NAME, TABLE_TYPE
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
          AND TABLE_NAME LIKE 'NSP%'
        ORDER BY TABLE_NAME
    """
    print(sqlcmd(client, sql_tabs_m, 'carmal_m'))

    # ─── B. Tablas de lotes en carmal_m ───────────────────────────────────
    print("\n═══ B. TABLAS DE LOTES / REQUISICIÓN EN carmal_m ═══")
    sql_tabs_lotes = """
        SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
          AND (TABLE_NAME LIKE '%Lote%'
            OR TABLE_NAME LIKE '%Requi%'
            OR TABLE_NAME LIKE '%Salida%'
            OR TABLE_NAME LIKE '%Compuesto%'
            OR TABLE_NAME LIKE '%Material%')
        ORDER BY TABLE_NAME
    """
    print(sqlcmd(client, sql_tabs_lotes, 'carmal_m'))

    # ─── C. Tablas de lotes en carmal_a ───────────────────────────────────
    print("\n═══ C. TABLAS DE LOTES EN carmal_a ═══")
    sql_tabs_a = """
        SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
          AND (TABLE_NAME LIKE '%Lote%'
            OR TABLE_NAME LIKE '%Compuesto%'
            OR TABLE_NAME LIKE '%Salida%')
        ORDER BY TABLE_NAME
    """
    print(sqlcmd(client, sql_tabs_a, 'carmal_a'))

    # ─── D. Columnas clave de NSPOrdenproduccion (carmal_m) ───────────────
    print("\n═══ D. COLUMNAS NSPOrdenproduccion (carmal_m) ═══")
    sql_cols_odp = """
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'NSPOrdenproduccion'
        ORDER BY ORDINAL_POSITION
    """
    print(sqlcmd(client, sql_cols_odp, 'carmal_m'))

    # ─── E. Columnas de tabla de requisición ──────────────────────────────
    print("\n═══ E. COLUMNAS NSPRequisicion / NSPRequisicionDetalle (carmal_m) ═══")
    for t in ['NSPRequisicion', 'NSPRequisicionDetalle', 'NSPRequisicionLote',
              'NSPOrdenproduccionRequisicion', 'NSPOrdenproduccionMaterial']:
        res = sqlcmd(client, f"""
            SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{t}' ORDER BY ORDINAL_POSITION
        """, 'carmal_m')
        if 'rows affected' in res and '0 rows' in res:
            continue
        if res and 'column_name' not in res.lower() or '---' in res:
            print(f"\n  ► {t}:")
            print(res)

    # ─── F. DIAGNÓSTICO ORDEN 0000009234 ──────────────────────────────────
    print(f"\n═══ F. ORDEN DE PRODUCCIÓN {ORDEN} en carmal_m ═══")
    sql_odp = f"""
        SELECT odp_num, art_num, descripcion,
               CONVERT(VARCHAR, fecha, 103) AS fecha,
               cantidad, estado, bodega
        FROM NSPOrdenproduccion
        WHERE odp_num = '{ORDEN}'
    """
    print(sqlcmd(client, sql_odp, 'carmal_m'))

    # ─── G. Requisiciones de la orden ─────────────────────────────────────
    print(f"\n═══ G. REQUISICIONES DE LA ORDEN {ORDEN} ═══")
    # Buscar en varias tablas posibles
    for tabla in ['NSPRequisicion', 'NSPOrdenproduccionRequisicion']:
        res = sqlcmd(client, f"""
            SELECT * FROM {tabla} WHERE odp_num = '{ORDEN}'
        """, 'carmal_m')
        if res and '0 rows' not in res:
            print(f"\n  Tabla {tabla}:")
            print(res)

    # ─── H. Artículo COMPUESTO 37 en ambas BDs ────────────────────────────
    print("\n═══ H. ARTÍCULO MP01D18X0... (COMPUESTO 37) en carmal_m ═══")
    sql_art_m = """
        SELECT art_num, descripcion, tipo
        FROM NSPArticulo
        WHERE descripcion LIKE '%COMPUESTO%37%'
           OR art_num LIKE 'MP01D18X0%'
    """
    print(sqlcmd(client, sql_art_m, 'carmal_m'))

    print("\n═══ H2. ARTÍCULO MP01D18X0... (COMPUESTO 37) en carmal_a ═══")
    sql_art_a = """
        SELECT co_art, art_des, tipo
        FROM saArticulo
        WHERE art_des LIKE '%COMPUESTO%37%'
           OR co_art LIKE 'MP01D18X0%'
    """
    print(sqlcmd(client, sql_art_a, 'carmal_a'))

    # ─── I. Lotes de COMPUESTO 37 en carmal_a ─────────────────────────────
    print("\n═══ I. LOTES DISPONIBLES de COMPUESTO 37 en carmal_a ═══")
    sql_lotes_comp = """
        SELECT le.co_art, le.co_alma, le.numero_lote,
               le.stock_actual, le.cantidad,
               CONVERT(VARCHAR, le.fecha_expiracion, 103) AS FecExp,
               CASE WHEN le.fecha_expiracion < GETDATE() THEN 'VENCIDO'
                    WHEN le.stock_actual <= 0 THEN 'SIN STOCK'
                    ELSE 'VIGENTE' END AS estado
        FROM saLoteEntrada le
        WHERE (le.co_art LIKE 'MP01D18X0%'
            OR le.co_art IN (
                SELECT co_art FROM saArticulo WHERE art_des LIKE '%COMPUESTO%37%'
            ))
        ORDER BY le.fecha_expiracion ASC, le.stock_actual DESC
    """
    print(sqlcmd(client, sql_lotes_comp, 'carmal_a'))

    # ─── J. Stock saStockAlmacen de COMPUESTO 37 ──────────────────────────
    print("\n═══ J. STOCK TOTAL (saStockAlmacen) COMPUESTO 37 ═══")
    sql_stock = """
        SELECT sa.co_art, a.art_des, sa.co_alma, sa.tipo, sa.stock
        FROM saStockAlmacen sa
        JOIN saArticulo a ON a.co_art = sa.co_art
        WHERE (sa.co_art LIKE 'MP01D18X0%'
            OR a.art_des LIKE '%COMPUESTO%37%')
        ORDER BY sa.co_alma, sa.tipo
    """
    print(sqlcmd(client, sql_stock, 'carmal_a'))

    # ─── K. Relación entre ambas BDs: links, linked servers, cross-db ─────
    print("\n═══ K. LINKED SERVERS / CROSS-DB REFERENCES ═══")
    sql_linked = """
        SELECT name, product, provider, data_source
        FROM sys.servers WHERE is_linked = 1
    """
    print(sqlcmd(client, sql_linked, 'master'))

    # ─── L. ¿carmal_m tiene referencias a carmal_a? ───────────────────────
    print("\n═══ L. TRIGGERS en carmal_m que referencian carmal_a ═══")
    sql_trg_ref = """
        SELECT t.name AS trigger_name, o.name AS tabla,
               SUBSTRING(sm.definition, 1, 300) AS fragmento
        FROM sys.sql_modules sm
        JOIN sys.triggers t ON t.object_id = sm.object_id
        JOIN sys.objects o ON o.object_id = t.parent_id
        WHERE sm.definition LIKE '%carmal_a%'
           OR sm.definition LIKE '%saLoteEntrada%'
           OR sm.definition LIKE '%saLoteSalida%'
    """
    print(sqlcmd(client, sql_trg_ref, 'carmal_m'))

    # ─── M. SPs en carmal_m con referencia a carmal_a ─────────────────────
    print("\n═══ M. STORED PROCEDURES en carmal_m con referencia a carmal_a ═══")
    sql_sp_ref = """
        SELECT ROUTINE_NAME
        FROM INFORMATION_SCHEMA.ROUTINES
        WHERE ROUTINE_DEFINITION LIKE '%carmal_a%'
           OR ROUTINE_DEFINITION LIKE '%saLoteSalida%'
    """
    print(sqlcmd(client, sql_sp_ref, 'carmal_m'))

    # ─── N. TODAS las tablas de carmal_m con conteo de filas ──────────────
    print("\n═══ N. INVENTARIO COMPLETO TABLAS carmal_m (con filas) ═══")
    sql_all_tabs = """
        SELECT t.name AS tabla,
               p.rows AS num_filas
        FROM sys.tables t
        JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id <= 1
        ORDER BY p.rows DESC
    """
    print(sqlcmd(client, sql_all_tabs, 'carmal_m'))

    client.close()

if __name__ == "__main__":
    run()
