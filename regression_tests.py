import paramiko
from datetime import datetime

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22
TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"
SQL_DB = "carmal_a"

PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️  WARN"

def sqlcmd(client, sql, db=SQL_DB):
    clean_sql = " ".join(sql.split()).replace('"', '\\"')
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -h -1 -Q "{clean_sql}" 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode(errors='replace').strip()

def get_val(client, sql):
    """Get a single numeric value"""
    result = sqlcmd(client, sql)
    lines = [l.strip() for l in result.split('\n') 
             if l.strip() and 'rows affected' not in l and '---' not in l]
    if lines:
        try:
            return int(lines[0].split()[0])
        except:
            return lines[0]
    return 0

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)

    print("=" * 70)
    print("SUITE DE PRUEBAS DE REGRESIÓN — Bug GCOM Consumo de Lotes")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Base de datos: carmal_a @ 192.168.1.205")
    print("=" * 70)

    results = []

    # ─────────────────────────────────────────────
    # RT-01: GCOMs huérfanos (sin vínculo a GenReng)
    # ─────────────────────────────────────────────
    print("\n[RT-01] GCOMs en saLoteSalida sin rowguid vinculado a saArtCompuestoGenReng")
    val = get_val(client, """
        SELECT COUNT(*) FROM saLoteSalida ls
        WHERE ls.tipo_doc = 'GCOM'
          AND NOT EXISTS (
              SELECT 1 FROM saArtCompuestoGenReng r 
              WHERE r.rowguid = ls.Rowguid_Lote
          )
    """)
    status = FAIL if int(val) > 0 else PASS
    print(f"  GCOMs huérfanos encontrados: {val}  →  {status}")
    results.append(("RT-01", status, f"{val} GCOMs sin vínculo"))

    # Detalle de GCOMs huérfanos
    detail = sqlcmd(client, """
        SELECT ls.co_art, ls.co_alma, ls.numero_lote, ls.cantidad, 
               CONVERT(VARCHAR, ls.fe_us_in, 120) AS fecha
        FROM saLoteSalida ls
        WHERE ls.tipo_doc = 'GCOM'
          AND NOT EXISTS (
              SELECT 1 FROM saArtCompuestoGenReng r 
              WHERE r.rowguid = ls.Rowguid_Lote
          )
        ORDER BY ls.fe_us_in DESC
    """)
    if detail.strip() and '0 rows' not in detail:
        print(f"  Detalle:\n{detail}")

    # ─────────────────────────────────────────────
    # RT-02: Renglones sin lote en generaciones cerradas
    # ─────────────────────────────────────────────
    print("\n[RT-02] Renglones con lote_asignado=0 en generaciones CERRADAS (gene_art=1)")
    val2 = get_val(client, """
        SELECT COUNT(*) FROM saArtCompuestoGenReng r
        JOIN saArtCompuestoGen g ON g.gene_num = r.gene_num
        WHERE g.gene_art = 1
          AND r.lote_asignado = 0
          AND g.fecha >= '2026-01-01'
    """)
    status2 = FAIL if int(val2) > 0 else PASS
    print(f"  Renglones sin lote en generaciones cerradas (2026): {val2}  →  {status2}")
    results.append(("RT-02", status2, f"{val2} renglones no asignados en gens cerradas"))

    # Generaciones afectadas
    detail2 = sqlcmd(client, """
        SELECT g.gene_num, COUNT(r.reng_num) AS reng_sin_lote,
               CONVERT(VARCHAR, g.fecha, 103) AS fecha
        FROM saArtCompuestoGenReng r
        JOIN saArtCompuestoGen g ON g.gene_num = r.gene_num
        WHERE g.gene_art = 1 AND r.lote_asignado = 0 AND g.fecha >= '2026-01-01'
        GROUP BY g.gene_num, g.fecha
        ORDER BY g.fecha DESC
    """)
    if detail2.strip() and '0 rows' not in detail2:
        print(f"  Generaciones afectadas:\n{detail2}")

    # ─────────────────────────────────────────────
    # RT-03: Lotes en P1-PS con stock_actual = cantidad (nunca descontados)
    # ─────────────────────────────────────────────
    print("\n[RT-03] Lotes vigentes en P1-PS con 0% de consumo (stock_actual = cantidad)")
    val3 = get_val(client, """
        SELECT COUNT(*) FROM saLoteEntrada le
        WHERE le.co_alma = 'P1-PS'
          AND le.stock_actual = le.cantidad
          AND le.cantidad > 0
          AND le.fecha_inicio >= '2026-01-01'
    """)
    detail3 = sqlcmd(client, """
        SELECT numero_lote, co_art, 
               CONVERT(VARCHAR, fecha_inicio, 103) AS FecIni,
               cantidad, stock_actual,
               (cantidad - stock_actual) AS consumido
        FROM saLoteEntrada
        WHERE co_alma = 'P1-PS'
          AND stock_actual = cantidad
          AND cantidad > 0
          AND fecha_inicio >= '2026-01-01'
        ORDER BY co_art, fecha_inicio DESC
    """)
    status3 = WARN  # Not necessarily a bug — some lots might be fresh
    print(f"  Lotes con 0% consumo en P1-PS (2026): {val3}  →  {status3}")
    print(f"  Detalle:\n{detail3}")
    results.append(("RT-03", status3, f"{val3} lotes sin consumo"))

    # ─────────────────────────────────────────────
    # RT-04: Rowguids duplicados en saArtCompuestoGenReng
    # ─────────────────────────────────────────────
    print("\n[RT-04] Rowguids duplicados en saArtCompuestoGenReng")
    val4 = get_val(client, """
        SELECT COUNT(*) FROM (
            SELECT rowguid, COUNT(*) as cnt
            FROM saArtCompuestoGenReng
            GROUP BY rowguid
            HAVING COUNT(*) > 1
        ) dup
    """)
    status4 = FAIL if int(val4) > 0 else PASS
    print(f"  rowguids duplicados: {val4}  →  {status4}")
    results.append(("RT-04", status4, f"{val4} rowguids duplicados"))

    # ─────────────────────────────────────────────
    # RT-05: Lote fantasma 3AX2112019 en P1-PS (stock debería ser 0)
    # ─────────────────────────────────────────────
    print("\n[RT-05] Lote vencido 3AX2112019 en P1-PS — stock_actual debería ser 0")
    detail5 = sqlcmd(client, """
        SELECT numero_lote, co_art, co_alma,
               CONVERT(VARCHAR, fecha_expiracion, 103) AS FecExp,
               cantidad, stock_actual,
               CASE WHEN stock_actual = 0 THEN 'OK' ELSE '*** STOCK FANTASMA ***' END AS estado
        FROM saLoteEntrada
        WHERE numero_lote = '3AX2112019' AND co_alma = 'P1-PS'
    """)
    status5 = FAIL if 'STOCK FANTASMA' in detail5 else PASS
    print(f"  {status5}\n{detail5}")
    results.append(("RT-05", status5, "Lote vencido 3AX2112019 con stock en P1-PS"))

    # ─────────────────────────────────────────────
    # RT-06: Triggers activos
    # ─────────────────────────────────────────────
    print("\n[RT-06] Triggers críticos activos")
    trg_detail = sqlcmd(client, """
        SELECT t.name, o.name AS tabla, 
               CASE WHEN t.is_disabled = 0 THEN 'ACTIVO' ELSE 'DESACTIVADO' END AS estado
        FROM sys.triggers t
        JOIN sys.objects o ON o.object_id = t.parent_id
        WHERE t.name IN ('TrigEstado_saArtCompuestoGen', 'ActualizarFechaLote', 
                         'trg_BlockLoteSinExistencia', 'ActualizarFechaLote_OLD')
    """)
    print(f"{trg_detail}")
    status6 = FAIL if 'TrigEstado_saArtCompuestoGen' not in trg_detail else PASS
    results.append(("RT-06", status6, "Estado de triggers"))

    # ─────────────────────────────────────────────
    # RT-07: Stock total sistema vs movimientos
    # ─────────────────────────────────────────────
    print("\n[RT-07] Consistencia saStockAlmacen vs sum(saLoteEntrada-saLoteSalida) para MP04N00X021")
    stock_sa = sqlcmd(client, """
        SELECT co_alma, stock FROM saStockAlmacen
        WHERE co_art = 'MP04N00X021' AND tipo = 'ACT'
        ORDER BY co_alma
    """)
    stock_calc = sqlcmd(client, """
        SELECT co_alma, SUM(cantidad) AS entradas,
               ISNULL((SELECT SUM(cantidad) FROM saLoteSalida ls 
                        WHERE ls.co_art = 'MP04N00X021' AND ls.co_alma = le.co_alma), 0) AS salidas,
               SUM(cantidad) - ISNULL((SELECT SUM(cantidad) FROM saLoteSalida ls 
                        WHERE ls.co_art = 'MP04N00X021' AND ls.co_alma = le.co_alma), 0) AS calculado
        FROM saLoteEntrada le WHERE co_art = 'MP04N00X021'
        GROUP BY co_alma ORDER BY co_alma
    """)
    print(f"  saStockAlmacen (ACT):\n{stock_sa}")
    print(f"  Calculado desde movimientos:\n{stock_calc}")
    results.append(("RT-07", WARN, "Revisar diferencias manualmente"))

    # ─────────────────────────────────────────────
    # RT-08: GCOMs de hoy correctamente reconciliados
    # ─────────────────────────────────────────────
    print("\n[RT-08] GCOMs del día de hoy y su estado de vinculación")
    today_detail = sqlcmd(client, """
        SELECT ls.co_art, ls.numero_lote, ls.cantidad,
               CONVERT(VARCHAR, ls.fe_us_in, 120) AS hora,
               CASE WHEN r.rowguid IS NULL THEN '*** HUERFANO ***' ELSE 'VINCULADO OK' END AS estado_vinculo,
               r.gene_num, r.lote_asignado
        FROM saLoteSalida ls
        LEFT JOIN saArtCompuestoGenReng r ON r.rowguid = ls.Rowguid_Lote
        WHERE ls.tipo_doc = 'GCOM'
          AND CAST(ls.fe_us_in AS DATE) = CAST(GETDATE() AS DATE)
        ORDER BY ls.fe_us_in DESC
    """)
    status8 = FAIL if 'HUERFANO' in today_detail else PASS
    print(f"  {status8}\n{today_detail}")
    results.append(("RT-08", status8, "GCOMs del día de hoy"))

    # ─────────────────────────────────────────────
    # RESUMEN FINAL
    # ─────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("RESUMEN DE PRUEBAS DE REGRESIÓN")
    print("=" * 70)
    passed = sum(1 for _, s, _ in results if s == PASS)
    failed = sum(1 for _, s, _ in results if s == FAIL)
    warned = sum(1 for _, s, _ in results if s == WARN)
    
    for test_id, status, desc in results:
        print(f"  {status}  [{test_id}] {desc}")
    
    print(f"\n  Total: {len(results)} pruebas | {passed} PASS | {failed} FAIL | {warned} WARN")
    
    if failed > 0:
        print(f"\n  🔴 SISTEMA REQUIERE CORRECCIÓN — {failed} prueba(s) fallaron")
    else:
        print(f"\n  🟢 SISTEMA OK")

    client.close()

if __name__ == "__main__":
    run()
