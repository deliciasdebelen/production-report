import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22
TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"

ORDEN  = "0000009234"
REQ    = "9736"
ART_C37 = "MP01D18X05-37"

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
    print(f"DIAGNÓSTICO PROFUNDO — Req {REQ} / Orden {ORDEN} / {ART_C37}")
    print("=" * 70)

    # 1. Orden de produccion completa
    print(f"\n[1] NSPOrdenproduccion {ORDEN}")
    sql1 = f"""
        SELECT odp_num, co_art, co_for, descripcion,
               CONVERT(VARCHAR, fecha, 103) AS fecha,
               cantidad, status, num_lote,
               CONVERT(VARCHAR, fe_us_in, 120) AS creado,
               CONVERT(VARCHAR, fe_us_mo, 120) AS modificado
        FROM NSPOrdenproduccion WHERE odp_num = '{ORDEN}'
    """
    print(sqlcmd(client, sql1, 'carmal_m'))

    # 2. Renglones de la orden
    print(f"\n[2] NSPOrdenproduccionreng — Materiales de {ORDEN}")
    sql2 = f"""
        SELECT reng_num, co_art, descripcion, cantidad,
               um, co_alma, num_lote,
               ISNULL(campo1,'') AS campo1, ISNULL(campo2,'') AS campo2
        FROM NSPOrdenproduccionreng
        WHERE odp_num = '{ORDEN}'
        ORDER BY reng_num
    """
    print(sqlcmd(client, sql2, 'carmal_m'))

    # 3. Requisición completa
    print(f"\n[3] NSPRequisicion {REQ}")
    sql3 = f"""
        SELECT req_num, odp_num, CONVERT(VARCHAR, fecha, 103) AS fecha,
               descripcion, CONFIRMA, ESTATUS, tras_num
        FROM NSPRequisicion WHERE req_num = {REQ}
    """
    print(sqlcmd(client, sql3, 'carmal_m'))

    # 4. Renglones de la requisición
    print(f"\n[4] NSPRequisicionreng — Renglones de Req {REQ}")
    sql4 = f"""
        SELECT * FROM NSPRequisicionreng WHERE req_num = {REQ}
        ORDER BY reng_num
    """
    # First get columns
    cols = sqlcmd(client, """
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'NSPRequisicionreng' ORDER BY ORDINAL_POSITION
    """, 'carmal_m')
    print(f"  Columnas: {cols}")
    print(sqlcmd(client, sql4, 'carmal_m'))

    # 5. Traslado asociado (tras_num)
    print(f"\n[5] TRASLADO ASOCIADO A LA REQUISICIÓN (tras_num = 0000018544)")
    # En carmal_a buscar el traslado
    sql5 = """
        SELECT tras_num, co_art, co_alma_sal, co_alma_ent,
               CONVERT(VARCHAR, fecha, 103) AS fecha,
               anulado, conf_sal, conf_ent
        FROM saTrasladoEntreAlmacen
        WHERE tras_num = '0000018544'
    """
    print(sqlcmd(client, sql5, 'carmal_a'))

    # 6. Renglones del traslado
    print(f"\n[6] RENGLONES DEL TRASLADO 0000018544")
    sql6 = """
        SELECT reng_num, co_art, descripcion, cantidad, num_lote,
               co_alma_sal, co_alma_ent
        FROM saTrasladoEntreAlmacenReng
        WHERE tras_num = '0000018544'
        ORDER BY reng_num
    """
    print(sqlcmd(client, sql6, 'carmal_a'))

    # 7. Lotes del COMPUESTO 37 en P1-PP1 (donde está el stock 7.91)
    print(f"\n[7] LOTES DE {ART_C37} EN P1-PP1 — DETALLE COMPLETO")
    sql7 = f"""
        SELECT numero_lote, stock_actual, cantidad,
               CONVERT(VARCHAR, fecha_inicio, 103) AS FecIni,
               CONVERT(VARCHAR, fecha_expiracion, 103) AS FecExp,
               CASE WHEN fecha_expiracion < GETDATE() THEN '*** VENCIDO ***'
                    WHEN stock_actual <= 0 THEN 'SIN STOCK'
                    ELSE 'VIGENTE' END AS estado,
               rowguid_reng
        FROM saLoteEntrada
        WHERE co_art = '{ART_C37}' AND co_alma = 'P1-PP1'
        ORDER BY fecha_expiracion ASC
    """
    print(sqlcmd(client, sql7, 'carmal_a'))

    # 8. ¿Hay lotes de C37 en P1-PS (almacen de sala)?
    print(f"\n[8] LOTES DE {ART_C37} EN P1-PS")
    sql8 = f"""
        SELECT numero_lote, stock_actual, cantidad,
               CONVERT(VARCHAR, fecha_expiracion, 103) AS FecExp,
               CASE WHEN fecha_expiracion < GETDATE() THEN '*** VENCIDO ***'
                    WHEN stock_actual <= 0 THEN 'SIN STOCK'
                    ELSE 'VIGENTE' END AS estado
        FROM saLoteEntrada
        WHERE co_art = '{ART_C37}' AND co_alma = 'P1-PS'
        ORDER BY fecha_expiracion ASC
    """
    print(sqlcmd(client, sql8, 'carmal_a'))

    # 9. Salidas de C37 (saLoteSalida) — ¿hay movimientos?
    print(f"\n[9] MOVIMIENTOS saLoteSalida DE {ART_C37}")
    sql9 = f"""
        SELECT tipo_doc, co_alma, numero_lote, cantidad,
               CONVERT(VARCHAR, fe_us_in, 120) AS fecha
        FROM saLoteSalida
        WHERE co_art = '{ART_C37}'
        ORDER BY fe_us_in DESC
    """
    print(sqlcmd(client, sql9, 'carmal_a'))

    # 10. La FECHA DE VENCIMIENTO del C37 — el error de la imagen
    # Los lotes C37-260521 y C37-260522 tienen FecExp 22/05/2026 y 25/05/2026
    # Hoy es 26/05/2026 — TODOS ESTÁN VENCIDOS
    print(f"\n[10] ANÁLISIS DE VENCIMIENTOS — Fecha actual vs lotes")
    sql10 = f"""
        SELECT CONVERT(VARCHAR, GETDATE(), 103) AS fecha_hoy,
               COUNT(*) AS total_lotes,
               SUM(CASE WHEN fecha_expiracion < GETDATE() THEN 1 ELSE 0 END) AS vencidos,
               SUM(CASE WHEN fecha_expiracion >= GETDATE() AND stock_actual > 0 THEN 1 ELSE 0 END) AS vigentes_con_stock,
               SUM(stock_actual) AS stock_total
        FROM saLoteEntrada
        WHERE co_art = '{ART_C37}'
    """
    print(sqlcmd(client, sql10, 'carmal_a'))

    # 11. ¿Hay lotes de C37 en CUALQUIER almacén con stock_actual > 0 y vigentes?
    print(f"\n[11] LOTES VIGENTES DE {ART_C37} EN TODOS LOS ALMACENES")
    sql11 = f"""
        SELECT co_alma, numero_lote, stock_actual,
               CONVERT(VARCHAR, fecha_expiracion, 103) AS FecExp
        FROM saLoteEntrada
        WHERE co_art = '{ART_C37}'
          AND stock_actual > 0
          AND fecha_expiracion >= GETDATE()
        ORDER BY fecha_expiracion ASC
    """
    res11 = sqlcmd(client, sql11, 'carmal_a')
    print(res11 if res11 and '0 rows' not in res11 else ">>> NO HAY LOTES VIGENTES CON STOCK <<<")

    # 12. Generaciones de C37 — últimas en carmal_a
    print(f"\n[12] ÚLTIMAS GENERACIONES DE {ART_C37} EN carmal_a")
    sql12 = f"""
        SELECT g.gene_num, g.co_art, g.co_alma,
               CONVERT(VARCHAR, g.fecha, 103) AS fecha,
               g.total_art, g.gene_art,
               CASE WHEN g.gene_art = 1 THEN 'CERRADA' ELSE 'ABIERTA' END AS estado
        FROM saArtCompuestoGen g
        WHERE g.co_art = '{ART_C37}'
        ORDER BY g.fecha DESC
    """
    print(sqlcmd(client, sql12, 'carmal_a'))

    # 13. NSPRequisicionreng columnas
    print("\n[13] COLUMNAS NSPRequisicionreng")
    sql13 = """
        SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'NSPRequisicionreng'
        ORDER BY ORDINAL_POSITION
    """
    print(sqlcmd(client, sql13, 'carmal_m'))

    client.close()

if __name__ == "__main__":
    run()
