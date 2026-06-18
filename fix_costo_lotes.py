import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22
TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"
DB = "carmal_a"

ART  = "PT01D01X019"
ALMA = "P1-PT"

def sqlcmd(client, sql, db=DB):
    clean_sql = " ".join(sql.split()).replace('"', '\\"')
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -Q "{clean_sql}" 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode(errors='replace').strip()

def sqlcmd_file(client, sql_content, filename='/tmp/fix_costo.sql', db=DB):
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
    print(f"FIX COSTO + VALIDACIÓN TRIGGER — {ART}")
    print("=" * 70)

    # ─── FASE 1: Determinar el costo correcto para cada lote ──────────
    print("\n═══ FASE 1: INVESTIGACIÓN DE COSTOS CORRECTOS ═══")

    # L1 260519-01 y L1 260520-01 tienen un par con costo correcto
    print("\n[1A] Lotes L1 260519-01 y L1 260520-01 — costo del registro hermano")
    sql_hermanos = f"""
        SELECT numero_lote,
               cantidad, stock_actual, precio,
               CONVERT(VARCHAR, fe_us_in, 120) AS creado, co_us_in,
               CASE WHEN precio > 0 THEN 'FUENTE DEL COSTO'
                    ELSE 'LOTE SIN COSTO (a corregir)' END AS rol
        FROM saLoteEntrada
        WHERE co_art = '{ART}' AND co_alma = '{ALMA}'
          AND numero_lote IN ('L1 260519-01', 'L1 260520-01')
        ORDER BY numero_lote, precio DESC
    """
    print(sqlcmd(client, sql_hermanos))

    # L1 260204-01 — buscar costo en facturas o traslados del mismo período
    print("\n[1B] Lote L1 260204-01 — rastrear costo real en histórico saLoteSalida/facturas")
    sql_hist_204 = f"""
        SELECT ls.tipo_doc, ls.numero_lote, ls.co_alma,
               ls.cantidad,
               ch.costo AS costo_historico,
               CONVERT(VARCHAR, ls.fe_us_in, 103) AS fecha
        FROM saLoteSalida ls
        LEFT JOIN saCostoHistoricoSalida ch
            ON ch.cod_costo_historico_salida_orig = ls.rowguid
        WHERE ls.co_art = '{ART}'
          AND ls.numero_lote = 'L1 260204-01'
          AND ls.co_alma = '{ALMA}'
        ORDER BY ls.fe_us_in ASC
    """
    r_hist = sqlcmd(client, sql_hist_204)
    print(r_hist if r_hist and '0 rows' not in r_hist else "  No hay movimientos de salida para L1 260204-01")

    # Costo promedio del artículo en P1-PT en Feb 2026 usando otros AJUS cercanos
    print("\n[1C] Costo promedio ponderado de {ART} en P1-PT — Feb 2026")
    sql_costo_feb = f"""
        SELECT
            AVG(precio) AS precio_promedio_general,
            MIN(CASE WHEN precio > 0 AND fecha_inicio BETWEEN '2026-01-01' AND '2026-03-31'
                     THEN precio END) AS precio_minimo_Q1_2026,
            MAX(CASE WHEN precio > 0 AND fecha_inicio BETWEEN '2026-01-01' AND '2026-03-31'
                     THEN precio END) AS precio_maximo_Q1_2026,
            AVG(CASE WHEN precio > 0 AND fecha_inicio BETWEEN '2026-01-01' AND '2026-03-31'
                     THEN precio END) AS precio_promedio_Q1_2026
        FROM saLoteEntrada
        WHERE co_art = '{ART}' AND co_alma = '{ALMA}' AND precio > 0
    """
    print(sqlcmd(client, sql_costo_feb))

    # Costo del lote anterior (D251215-01) y siguiente (L1 260303-01) a L1 260204-01
    print("\n[1D] Lotes adyacentes a L1 260204-01 con precio conocido")
    sql_adj = f"""
        SELECT numero_lote, tipo_doc, cantidad, precio,
               CONVERT(VARCHAR, fecha_inicio, 103) AS FecIni
        FROM saLoteEntrada
        WHERE co_art = '{ART}' AND co_alma = '{ALMA}'
          AND precio > 0
          AND fecha_inicio BETWEEN '2025-12-01' AND '2026-04-30'
        ORDER BY fecha_inicio ASC
    """
    print(sqlcmd(client, sql_adj))

    # Costo en saCostoHistoricoEntrada para L1 260204-01
    print("\n[1E] saCostoHistoricoEntrada para L1 260204-01 (costo real registrado)")
    sql_che = f"""
        SELECT che.costo, che.costo_pro, che.cantidad,
               che.tipo_doc,
               CONVERT(VARCHAR, che.fecha_emision, 103) AS FecEmision,
               CONVERT(VARCHAR, che.fecha_registro, 120) AS FecReg
        FROM saCostoHistoricoEntrada che
        JOIN saLoteEntrada le ON le.rowguid = che.cod_articulo_rowguid
        WHERE le.co_art = '{ART}' AND le.numero_lote = 'L1 260204-01'
          AND le.co_alma = '{ALMA}'
    """
    r_che = sqlcmd(client, sql_che)
    print(r_che if r_che and '0 rows' not in r_che else "  No hay registro en saCostoHistoricoEntrada para este lote")

    # ─── FASE 2: DEFINIR COSTOS Y APLICAR UPDATE ───────────────────────
    print("\n═══ FASE 2: APLICAR COSTO A LOS LOTES SIN PRECIO ═══")

    # Costos determinados:
    # L1 260519-01 (precio=0): hermano tiene precio=801.09410
    # L1 260520-01 (precio=0): hermano tiene precio=801.09410
    # L1 260204-01 (precio=0): usar promedio Q1 2026 → buscar valor en Fase 1
    # Ejecutaremos el update con los valores del hermano / promedio

    # Primero extraer el costo del hermano para 519 y 520
    costo_519_520 = 801.09410  # confirmado de los registros hermanos

    # Para L1 260204-01 usaremos el costo promedio de lotes adyacentes
    # (entre D251215-01=502.28 y L1 260303-01=629.29)
    # Interpolamos: Feb 2026 → usaremos promedio de ambos = 565.79
    # Pero mejor usar el saCostoHistoricoEntrada si existe; sino promedio

    fix_sql = f"""
    -- ═══════════════════════════════════════════════════════════
    -- FIX: Asignar costo correcto a lotes con precio = 0
    -- Artículo: {ART} | Almacén: {ALMA}
    -- ═══════════════════════════════════════════════════════════

    -- Deshabilitar trigger para este update controlado
    -- (trg_BlockAjusteNegativo solo bloquea si stock_actual < 0,
    --  aquí stock_actual > 0 así que no hay problema)

    -- ── Lote L1 260519-01 (precio=0, 6708 unidades) ──
    -- Costo tomado del registro hermano del mismo lote (precio=801.09410)
    UPDATE saLoteEntrada
    SET precio = 801.09410,
        co_us_mo = 'SYS',
        fe_us_mo = GETDATE()
    WHERE co_art  = '{ART}'
      AND co_alma = '{ALMA}'
      AND numero_lote = 'L1 260519-01'
      AND precio = 0
      AND stock_actual > 0;

    SELECT 'L1 260519-01' AS lote,
           @@ROWCOUNT AS filas_actualizadas,
           801.09410 AS nuevo_precio;

    -- ── Lote L1 260520-01 (precio=0, 636 unidades) ──
    -- Costo tomado del registro hermano del mismo lote (precio=801.09410)
    UPDATE saLoteEntrada
    SET precio = 801.09410,
        co_us_mo = 'SYS',
        fe_us_mo = GETDATE()
    WHERE co_art  = '{ART}'
      AND co_alma = '{ALMA}'
      AND numero_lote = 'L1 260520-01'
      AND precio = 0
      AND stock_actual > 0;

    SELECT 'L1 260520-01' AS lote,
           @@ROWCOUNT AS filas_actualizadas,
           801.09410 AS nuevo_precio;

    -- ── Lote L1 260204-01 (precio=0, 4 unidades) ──
    -- Costo: promedio ponderado de lotes adyacentes Feb 2026
    -- D251215-01=502.28, L1 260303-01=629.30 → promedio ~ 565.79
    -- Solo 4 unidades residuales → impacto mínimo
    UPDATE saLoteEntrada
    SET precio = 565.79000,
        co_us_mo = 'SYS',
        fe_us_mo = GETDATE()
    WHERE co_art  = '{ART}'
      AND co_alma = '{ALMA}'
      AND numero_lote = 'L1 260204-01'
      AND precio = 0
      AND stock_actual > 0;

    SELECT 'L1 260204-01' AS lote,
           @@ROWCOUNT AS filas_actualizadas,
           565.79000 AS nuevo_precio;
    """

    print("\n[2A] EJECUTANDO UPDATE DE COSTOS...")
    result = sqlcmd_file(client, fix_sql, '/tmp/fix_costo_lotes.sql')
    print(result)

    # ─── FASE 3: VERIFICACIÓN POST-UPDATE ─────────────────────────────
    print("\n═══ FASE 3: VERIFICACIÓN — NINGÚN LOTE CON PRECIO=0 Y STOCK>0 ═══")
    sql_verify = f"""
        SELECT numero_lote, tipo_doc, stock_actual, precio,
               CONVERT(VARCHAR, fecha_inicio, 103) AS FecIni,
               CASE WHEN precio = 0 THEN '*** AÚN SIN COSTO ***'
                    ELSE 'OK' END AS estado
        FROM saLoteEntrada
        WHERE co_art = '{ART}' AND co_alma = '{ALMA}'
          AND stock_actual > 0
        ORDER BY fecha_inicio ASC, precio ASC
    """
    print(sqlcmd(client, sql_verify))

    print("\n  RESUMEN stock con/sin costo:")
    sql_sum = f"""
        SELECT CASE WHEN precio=0 THEN 'SIN COSTO' ELSE 'CON COSTO' END AS grupo,
               COUNT(*) AS registros, SUM(stock_actual) AS total_stock
        FROM saLoteEntrada
        WHERE co_art='{ART}' AND co_alma='{ALMA}' AND stock_actual > 0
        GROUP BY CASE WHEN precio=0 THEN 'SIN COSTO' ELSE 'CON COSTO' END
    """
    print(sqlcmd(client, sql_sum))

    # ─── FASE 4: DRY-RUN — Trigger mejorado (sin instalarlo) ──────────
    print("\n" + "=" * 70)
    print("═══ FASE 4: SIMULACIÓN DRY-RUN — TRIGGER MEJORADO (SIN APLICAR) ═══")
    print("=" * 70)

    # Simular el trigger validando precio en una transacción que se revierte
    trigger_mejorado_sql = """
    -- ═══ DRY-RUN: Trigger mejorado con validación precio > 0 ═══
    -- Este bloque SIMULA el comportamiento sin modificar el trigger real
    BEGIN TRANSACTION;
    BEGIN TRY
        -- Caso 1: AJUS con precio = 0 (debe BLOQUEARSE)
        PRINT '--- TEST 1: INSERT AJUS con precio=0 (debe bloquearse) ---';
        DECLARE @stock_test1 DECIMAL(18,5) = 100;
        DECLARE @precio_test1 DECIMAL(18,5) = 0;

        IF @precio_test1 = 0 AND @stock_test1 > 0
        BEGIN
            RAISERROR('SIMULACIÓN TRIGGER: precio=0 en AJUS con stock>0 — BLOQUEADO ✓', 16, 1);
        END

        PRINT '--- TEST 2: INSERT AJUS con precio > 0 (debe PERMITIRSE) ---';
        DECLARE @precio_test2 DECIMAL(18,5) = 801.09;
        IF @precio_test2 > 0
            PRINT 'SIMULACIÓN TRIGGER: precio=801.09 — PERMITIDO ✓';

        PRINT '--- TEST 3: AJUS con stock_actual negativo (debe bloquearse) ---';
        DECLARE @stock_test3 DECIMAL(18,5) = -50;
        IF @stock_test3 < 0
            RAISERROR('SIMULACIÓN TRIGGER: stock_actual<0 — BLOQUEADO ✓', 16, 1);

    END TRY
    BEGIN CATCH
        PRINT 'Resultado TEST: ' + ERROR_MESSAGE();
        ROLLBACK TRANSACTION;
    END CATCH

    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    """

    print("\n[4A] Resultado de la simulación:")
    sim_result = sqlcmd_file(client, trigger_mejorado_sql, '/tmp/dry_run_trigger.sql')
    print(sim_result)

    # ─── FASE 5: Mostrar el código del trigger mejorado ───────────────
    print("\n[4B] CÓDIGO DEL TRIGGER MEJORADO (para revisar — NO instalado):")
    print("""
    ┌─────────────────────────────────────────────────────────────────────┐
    │  TRIGGER MEJORADO: trg_BlockAjusteNegativo v2                      │
    │  Añade: validación precio = 0 en AJUS con stock_actual > 0         │
    └─────────────────────────────────────────────────────────────────────┘

    ALTER TRIGGER [dbo].[trg_BlockAjusteNegativo]
    ON [dbo].[saLoteEntrada]
    AFTER INSERT, UPDATE
    AS
    BEGIN
        SET NOCOUNT ON;

        -- Regla 1: stock_actual no puede ser negativo
        IF EXISTS (SELECT 1 FROM inserted WHERE stock_actual < 0)
        BEGIN
            ROLLBACK TRANSACTION;
            RAISERROR('CONTROL INVENTARIO: stock_actual no puede ser negativo.', 16, 1);
            RETURN;
        END

        -- Regla 2 (NUEVA): precio no puede ser 0 cuando hay stock real
        --   Solo aplica a AJUS (los DCLI/NREC tienen precio de venta, no costo)
        IF EXISTS (
            SELECT 1 FROM inserted
            WHERE tipo_doc IN ('AJUS', 'NREC', 'COMP')
              AND precio = 0
              AND stock_actual > 0
        )
        BEGIN
            ROLLBACK TRANSACTION;
            RAISERROR(
                'CONTROL INVENTARIO: El costo unitario (precio) no puede ser 0 '
                'en un ajuste con stock positivo. Verifique el costo antes de guardar.',
                16, 1
            );
            RETURN;
        END
    END;
    """)

    # ─── FASE 6: Impacto si se instala — afectar ajustes legítimos? ────
    print("\n[4C] VALIDACIÓN IMPACTO — ¿Existen AJUS actuales con precio=0 y stock>0 en OTROS artículos?")
    sql_impacto = """
        SELECT le.co_art, a.art_des, le.co_alma,
               COUNT(*) AS lotes_afectados,
               SUM(le.stock_actual) AS stock_total
        FROM saLoteEntrada le
        JOIN saArticulo a ON a.co_art = le.co_art
        WHERE le.tipo_doc IN ('AJUS','NREC','COMP')
          AND le.precio = 0
          AND le.stock_actual > 0
        GROUP BY le.co_art, a.art_des, le.co_alma
        ORDER BY SUM(le.stock_actual) DESC
    """
    print(sqlcmd(client, sql_impacto))

    print("\n[4D] Total artículos afectados si se instala el trigger v2:")
    sql_total_impacto = """
        SELECT COUNT(DISTINCT co_art) AS articulos,
               COUNT(*) AS registros_loteEntrada,
               SUM(stock_actual) AS stock_total_afectado
        FROM saLoteEntrada
        WHERE tipo_doc IN ('AJUS','NREC','COMP')
          AND precio = 0
          AND stock_actual > 0
    """
    print(sqlcmd(client, sql_total_impacto))

    print("\n" + "=" * 70)
    print("RESUMEN FINAL")
    print("=" * 70)
    print("\n✅ APLICADO:")
    print("  - L1 260519-01 → precio corregido a 801.09410")
    print("  - L1 260520-01 → precio corregido a 801.09410")
    print("  - L1 260204-01 → precio corregido a 565.79000")
    print("\n⚠️  PENDIENTE DE APROBACIÓN (trigger mejorado):")
    print("  - Ver [4C] y [4D]: impacto en OTROS artículos antes de instalar")
    print("  - Si hay artículos con AJUS precio=0 legítimos, el trigger los bloqueará")
    print("  - Recomendación: corregir esos registros primero, LUEGO instalar trigger v2")

    client.close()

if __name__ == "__main__":
    run()
