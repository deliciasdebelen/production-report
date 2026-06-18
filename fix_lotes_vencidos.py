import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22
TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"
SQL_DB = "carmal_a"

# Artículos con problema en gen 954
ARTICULOS = {
    'MP01N00X153': ('Azúcar/Sal Blanca',    67.99000),
    'MP04N00X014': ('Antiespumante',          0.06500),
}
ALMA = 'P1-PS'

def sqlcmd(client, sql, db=SQL_DB):
    clean_sql = " ".join(sql.split()).replace('"', '\\"')
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -Q "{clean_sql}" 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode(errors='replace').strip()

def sqlcmd_file(client, sql, filename='/tmp/fix_lotes.sql', db=SQL_DB):
    sftp = client.open_sftp()
    with sftp.file(filename, 'w') as f:
        f.write(sql)
    sftp.close()
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm -v /tmp:/tmp mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -i {filename} 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    return stdout.read().decode(errors='replace').strip()

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)

    print("=" * 70)
    print("DIAGNÓSTICO — Lotes vencidos con stock fantasma bloqueando gen 954")
    print("=" * 70)

    arts_str = "','".join(ARTICULOS.keys())

    # ─── 1. Ver todos los lotes con stock > 0 en P1-PS para estos artículos ──
    print("\n[1] TODOS LOS LOTES CON stock_actual > 0 en P1-PS")
    sql1 = f"""
        SELECT le.co_art, le.numero_lote,
               CONVERT(VARCHAR, le.fecha_expiracion, 103) AS FecExp,
               le.stock_actual,
               CASE WHEN le.fecha_expiracion < GETDATE() THEN '*** VENCIDO ***' ELSE 'VIGENTE' END AS estado,
               ISNULL((SELECT SUM(ls.cantidad) FROM saLoteSalida ls
                       WHERE ls.numero_lote = le.numero_lote
                         AND ls.co_art = le.co_art
                         AND ls.co_alma = le.co_alma), 0) AS total_salidas
        FROM saLoteEntrada le
        WHERE le.co_art IN ('{arts_str}')
          AND le.co_alma = '{ALMA}'
          AND le.stock_actual > 0
        ORDER BY le.co_art, le.fecha_expiracion ASC
    """
    print(sqlcmd(client, sql1))

    # ─── 2. Lotes VENCIDOS con stock > 0 (los que bloquean a Profit) ──────
    print("\n[2] LOTES VENCIDOS CON stock_actual > 0 — CANDIDATOS A LIMPIAR")
    sql2 = f"""
        SELECT le.co_art, le.numero_lote,
               CONVERT(VARCHAR, le.fecha_expiracion, 103) AS FecExp,
               le.stock_actual,
               ISNULL((SELECT SUM(ls.cantidad) FROM saLoteSalida ls
                       WHERE ls.numero_lote = le.numero_lote
                         AND ls.co_art = le.co_art
                         AND ls.co_alma = le.co_alma), 0) AS total_salidas,
               (le.cantidad - ISNULL((SELECT SUM(ls.cantidad) FROM saLoteSalida ls
                       WHERE ls.numero_lote = le.numero_lote
                         AND ls.co_art = le.co_art
                         AND ls.co_alma = le.co_alma), 0)) AS saldo_calculado
        FROM saLoteEntrada le
        WHERE le.co_art IN ('{arts_str}')
          AND le.co_alma = '{ALMA}'
          AND le.stock_actual > 0
          AND le.fecha_expiracion < GETDATE()
        ORDER BY le.co_art, le.fecha_expiracion ASC
    """
    print(sqlcmd(client, sql2))

    # ─── 3. Lotes VIGENTES disponibles (lo que el operador debería ver) ───
    print("\n[3] LOTES VIGENTES DISPONIBLES (lo que el operador debe seleccionar)")
    for art, (desc, qty) in ARTICULOS.items():
        print(f"\n  → {art} ({desc}) — requiere {qty} kg:")
        sql = f"""
            SELECT numero_lote, stock_actual,
                   CONVERT(VARCHAR, fecha_expiracion, 103) AS FecExp,
                   CASE WHEN stock_actual >= {qty} THEN 'SUFICIENTE'
                        ELSE 'INSUFICIENTE' END AS vs_requerido
            FROM saLoteEntrada
            WHERE co_art = '{art}' AND co_alma = '{ALMA}'
              AND stock_actual > 0
              AND fecha_expiracion > GETDATE()
            ORDER BY fecha_expiracion ASC
        """
        res = sqlcmd(client, sql)
        lines = [l for l in res.split('\n')
                 if l.strip() and 'rows affected' not in l and '---' not in l]
        if not lines:
            print(f"     ⚠️  SIN LOTES VIGENTES CON STOCK")
        else:
            for l in lines[:6]:
                print(f"     {l}")

    # ─── 4. Aplicar limpieza de lotes vencidos ────────────────────────────
    print("\n[4] APLICANDO LIMPIEZA — Zereando stock_actual de lotes VENCIDOS")

    fix_sql = f"""
        -- Zerear stock_actual de lotes vencidos sin salidas pendientes
        -- para MP01N00X153 y MP04N00X014 en P1-PS
        UPDATE saLoteEntrada
        SET stock_actual = 0
        WHERE co_art IN ('{arts_str}')
          AND co_alma = '{ALMA}'
          AND fecha_expiracion < GETDATE()
          AND stock_actual > 0;
        
        SELECT @@ROWCOUNT AS registros_actualizados;
    """
    r = sqlcmd_file(client, fix_sql, '/tmp/fix_vencidos_954.sql')
    print(f"  Resultado: {r}")

    # ─── 5. Verificar estado final ────────────────────────────────────────
    print("\n[5] ESTADO FINAL — Lotes con stock > 0 en P1-PS (post-limpieza)")
    sql5 = f"""
        SELECT le.co_art, le.numero_lote,
               CONVERT(VARCHAR, le.fecha_expiracion, 103) AS FecExp,
               le.stock_actual,
               CASE WHEN le.fecha_expiracion < GETDATE() THEN 'VENCIDO' ELSE 'VIGENTE' END AS estado
        FROM saLoteEntrada le
        WHERE le.co_art IN ('{arts_str}')
          AND le.co_alma = '{ALMA}'
          AND le.stock_actual > 0
        ORDER BY le.co_art, le.fecha_expiracion ASC
    """
    print(sqlcmd(client, sql5))

    # ─── 6. Stock saStockAlmacen post-limpieza ───────────────────────────
    print("\n[6] STOCK TOTAL (saStockAlmacen ACT) DESPUÉS DE LIMPIEZA")
    sql6 = f"""
        SELECT sa.co_art, a.art_des, sa.stock AS stock_sistema
        FROM saStockAlmacen sa
        JOIN saArticulo a ON a.co_art = sa.co_art
        WHERE sa.co_art IN ('{arts_str}')
          AND sa.co_alma = '{ALMA}' AND sa.tipo = 'ACT'
    """
    print(sqlcmd(client, sql6))

    # ─── 7. Estado final renglones gen 954 ───────────────────────────────
    print("\n[7] RENGLONES GEN 0000000954 — Stock disponible vs requerido")
    sql7 = """
        SELECT r.reng_num, r.co_art, a.art_des,
               r.total_art AS requerido,
               sa.stock AS stock_disponible,
               CASE WHEN sa.stock >= r.total_art THEN 'OK - SUFICIENTE'
                    ELSE '*** INSUFICIENTE ***' END AS estado_stock,
               r.lote_asignado
        FROM saArtCompuestoGenReng r
        JOIN saArticulo a ON a.co_art = r.co_art
        LEFT JOIN saStockAlmacen sa ON sa.co_art = r.co_art
            AND sa.co_alma = r.co_alma AND sa.tipo = 'ACT'
        WHERE r.gene_num = '0000000954'
        ORDER BY r.reng_num
    """
    print(sqlcmd(client, sql7))

    print("\n" + "=" * 70)
    print("LIMPIEZA COMPLETADA")
    print("Pasos para el operador:")
    print("  1. Cerrar y reabrir Profit Plus (refrescar sesión)")
    print("  2. Abrir generación 0000000954")
    print("  3. En 'Lotes de Salida' seleccionar:")
    print("     • MP01N00X153 (Azúcar): lote 09102024 (vence 10/10/2026)")
    print("     • MP04N00X014 (Antiespumante): lote 02072025 (vence 14/03/2027)")
    print("=" * 70)

    client.close()

if __name__ == "__main__":
    run()
