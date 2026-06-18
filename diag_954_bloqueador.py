import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22
TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"
SQL_DB = "carmal_a"

GEN = "0000000954"

def sqlcmd(client, sql, db=SQL_DB):
    clean_sql = " ".join(sql.split()).replace('"', '\\"')
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -Q "{clean_sql}" 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode(errors='replace').strip()

def sqlcmd_file(client, sql_content, filename='/tmp/diag954b.sql', db=SQL_DB):
    sftp = client.open_sftp()
    with sftp.file(filename, 'w') as f:
        f.write(sql_content)
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
    print(f"DIAGNÓSTICO BLOQUEADOR — Gen {GEN} no inserta GCOMs")
    print("=" * 70)

    # 1. Lotes disponibles para cada ingrediente de gen 954
    print(f"\n[1] LOTES DISPONIBLES POR CADA INGREDIENTE DE {GEN}")
    ingredientes = [
        ('MP01N00X153', 67.99000),
        ('MP04N00X021', 0.19500),
        ('MP04N00X013', 0.18200),
        ('MP04N00X014', 0.06500),
        ('MP04N00X023', 0.20800),
    ]
    for art, qty in ingredientes:
        sql = f"""
            SELECT '{art}' AS co_art, numero_lote, co_alma,
                   CONVERT(VARCHAR, fecha_expiracion, 103) AS FecExp,
                   stock_actual,
                   CASE WHEN fecha_expiracion < GETDATE() THEN 'VENCIDO'
                        WHEN stock_actual <= 0 THEN 'SIN STOCK'
                        WHEN stock_actual < {qty} THEN 'STOCK INSUF'
                        ELSE 'OK' END AS estado
            FROM saLoteEntrada
            WHERE co_art = '{art}' AND co_alma = 'P1-PS'
              AND stock_actual > 0
            ORDER BY fecha_expiracion ASC
        """
        res = sqlcmd(client, sql)
        lines = [l for l in res.split('\n') if l.strip() and 'rows affected' not in l and '---' not in l]
        if not lines:
            print(f"  {art} (need {qty}): >>> SIN LOTES CON STOCK EN P1-PS <<<")
        else:
            print(f"  {art} (need {qty}):")
            for l in lines[:5]:
                print(f"    {l}")

    # 2. Verificar el trigger trg_BlockLoteSinExistencia — podría estar bloqueando
    print("\n[2] CÓDIGO DEL TRIGGER trg_BlockLoteSinExistencia")
    sql2 = "SELECT OBJECT_DEFINITION(OBJECT_ID('trg_BlockLoteSinExistencia'))"
    print(sqlcmd(client, sql2))

    # 3. Simular el INSERT que haría Profit y ver si el trigger lo bloquea
    # El trigger revisa que stock_actual >= cantidad tras el INSERT
    print("\n[3] SIMULACIÓN: ¿Qué pasaría si Profit insertara un GCOM para MP04N00X021?")
    # Buscar el rowguid del lote a usar
    sql3 = """
        SELECT TOP 1 rowguid, numero_lote, stock_actual
        FROM saLoteEntrada
        WHERE co_art = 'MP04N00X021' AND co_alma = 'P1-PS'
          AND stock_actual >= 0.195
          AND fecha_expiracion > GETDATE()
        ORDER BY fecha_expiracion ASC
    """
    print("  Mejor lote disponible para MP04N00X021:")
    print(sqlcmd(client, sql3))

    # 4. Ver el stock_actual en saLoteEntrada para los lotes que Profit usaría
    # Y verificar si el trigger de bloqueo rechazaría el movimiento
    print("\n[4] STOCK ACUMULADO POR LOTE (P1-PS) — Artículos de gen 954")
    for art, qty in ingredientes:
        sql = f"""
            SELECT co_art, co_alma, numero_lote,
                   CONVERT(VARCHAR, fecha_expiracion, 103) AS FecExp,
                   stock_actual,
                   CASE WHEN stock_actual >= {qty} THEN 'SUFICIENTE'
                        WHEN stock_actual > 0 THEN 'INSUFICIENTE'
                        ELSE 'CERO' END AS vs_requerido
            FROM saLoteEntrada
            WHERE co_art = '{art}' AND co_alma = 'P1-PS'
              AND fecha_expiracion > GETDATE()
              AND stock_actual > 0
            ORDER BY fecha_expiracion ASC
        """
        print(f"\n  → {art} (requiere {qty} kg):")
        res = sqlcmd(client, sql)
        lines = [l for l in res.split('\n') if l.strip() and 'rows affected' not in l and '---' not in l]
        if not lines:
            print(f"     *** SIN LOTES VIGENTES CON STOCK ***")
        else:
            for l in lines[:5]:
                print(f"     {l}")

    # 5. Buscar en saStockAlmacen el stock total disponible
    print("\n[5] STOCK TOTAL saStockAlmacen (ACT) para ingredientes de gen 954")
    arts = "','".join([a for a, _ in ingredientes])
    sql5 = f"""
        SELECT sa.co_art, a.art_des, sa.co_alma, sa.tipo, sa.stock
        FROM saStockAlmacen sa
        JOIN saArticulo a ON a.co_art = sa.co_art
        WHERE sa.co_art IN ('{arts}')
          AND sa.co_alma = 'P1-PS'
          AND sa.tipo = 'ACT'
        ORDER BY sa.co_art
    """
    print(sqlcmd(client, sql5))

    # 6. Ver si hay algún bloqueo de tabla activo (sesiones bloqueando)
    print("\n[6] SESIONES ACTIVAS / BLOQUEOS EN saLoteSalida o saLoteEntrada")
    sql6 = """
        SELECT r.session_id, r.blocking_session_id, r.status,
               r.wait_type, r.wait_time,
               SUBSTRING(t.text, 1, 100) AS query_text,
               r.cpu_time, r.logical_reads
        FROM sys.dm_exec_requests r
        CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) t
        WHERE r.status != 'background'
          AND r.session_id != @@SPID
        ORDER BY r.cpu_time DESC
    """
    print(sqlcmd(client, sql6))

    # 7. Verificar si el trigger trg_AutoReconciliarGCOM pudo estar causando
    # un deadlock o rollback al insertarse el GCOM en medio de la transacción de Profit
    print("\n[7] ANÁLISIS: ¿El trigger trg_AutoReconciliarGCOM causa rollback?")
    print("""
  El trigger trg_AutoReconciliarGCOM ejecuta EXEC sp_ReconciliarLotesGCOM
  dentro de la misma transacción que el INSERT de Profit.
  
  Si sp_ReconciliarLotesGCOM falla o hace ROLLBACK, cancela también
  el INSERT de Profit → Profit no puede insertar el GCOM → lotes no se guardan.
  
  ESTO PODRÍA SER LA CAUSA DEL PROBLEMA EN GEN 954.
    """)

    # 8. Verificar el código del trigger para confirmar
    print("\n[8] CÓDIGO ACTUAL DEL TRIGGER trg_AutoReconciliarGCOM")
    sql8 = "SELECT OBJECT_DEFINITION(OBJECT_ID('trg_AutoReconciliarGCOM'))"
    print(sqlcmd(client, sql8))

    client.close()

if __name__ == "__main__":
    run()
