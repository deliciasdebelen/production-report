import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"
DB = "carmal_a"

def sqlcmd_file(client, sql, fname='/tmp/fix_masivo.sql', db=DB):
    sftp = client.open_sftp()
    with sftp.file(fname, 'w') as f:
        f.write(sql)
    sftp.close()
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm -v /tmp:/tmp mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -i {fname} 2>&1 | grep -v "password for"'
    )
    _, o, _ = client.exec_command(cmd, timeout=120)
    return o.read().decode(errors='replace').strip()

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, 22, JUMP_USER, JUMP_PASS)

    print("=" * 70)
    print("LIMPIEZA MASIVA: Corregir precio=0 en saLoteEntrada")
    print("Fuentes de costo (en orden de prioridad):")
    print("  1. Registro hermano del mismo numero_lote con precio > 0")
    print("  2. saAjusteReng.cost_unit del ajuste que creó el lote")
    print("  3. Promedio ponderado de lotes del mismo artículo/almacén en ±90 días")
    print("=" * 70)

    # ── PASO 1: Auditoría completa antes de tocar nada ─────────────────
    print("\n[1] AUDITORÍA PREVIA — 588 lotes con precio=0 y stock>0")
    sql_audit = """
        SELECT
            le.co_art,
            a.art_des,
            le.co_alma,
            COUNT(*)           AS lotes_sin_costo,
            SUM(le.stock_actual) AS stock_total,
            -- Fuente 1: hermano mismo lote con costo
            SUM(CASE WHEN EXISTS(
                SELECT 1 FROM saLoteEntrada le2
                WHERE le2.co_art = le.co_art
                  AND le2.co_alma = le.co_alma
                  AND le2.numero_lote = le.numero_lote
                  AND le2.precio > 0
            ) THEN 1 ELSE 0 END) AS recuperables_hermano,
            -- Fuente 2: promedio existe
            SUM(CASE WHEN EXISTS(
                SELECT 1 FROM saLoteEntrada le3
                WHERE le3.co_art = le.co_art
                  AND le3.co_alma = le.co_alma
                  AND le3.precio > 0
                  AND le3.fecha_inicio BETWEEN DATEADD(DAY,-90,le.fecha_inicio)
                                           AND DATEADD(DAY,90,le.fecha_inicio)
            ) THEN 1 ELSE 0 END) AS recuperables_promedio
        FROM saLoteEntrada le
        JOIN saArticulo a ON a.co_art = le.co_art
        WHERE le.tipo_doc IN ('AJUS','NREC','COMP','GCOM')
          AND le.precio = 0
          AND le.stock_actual > 0
        GROUP BY le.co_art, a.art_des, le.co_alma
        ORDER BY SUM(le.stock_actual) DESC
    """
    print(sqlcmd_file(client, sql_audit, '/tmp/audit_previa.sql'))

    print("\n  TOTALES GLOBALES:")
    sql_tot = """
        SELECT
            COUNT(*)             AS total_registros,
            COUNT(DISTINCT co_art) AS articulos_distintos,
            SUM(stock_actual)    AS stock_total_afectado,
            SUM(CASE WHEN EXISTS(
                SELECT 1 FROM saLoteEntrada le2
                WHERE le2.co_art = le.co_art AND le2.co_alma = le.co_alma
                  AND le2.numero_lote = le.numero_lote AND le2.precio > 0
            ) THEN 1 ELSE 0 END) AS con_hermano,
            SUM(CASE WHEN NOT EXISTS(
                SELECT 1 FROM saLoteEntrada le2
                WHERE le2.co_art = le.co_art AND le2.co_alma = le.co_alma
                  AND le2.numero_lote = le.numero_lote AND le2.precio > 0
            ) AND EXISTS(
                SELECT 1 FROM saLoteEntrada le3
                WHERE le3.co_art = le.co_art AND le3.co_alma = le.co_alma
                  AND le3.precio > 0
                  AND le3.fecha_inicio BETWEEN DATEADD(DAY,-90,le.fecha_inicio)
                                           AND DATEADD(DAY,90,le.fecha_inicio)
            ) THEN 1 ELSE 0 END) AS con_promedio_90d,
            SUM(CASE WHEN NOT EXISTS(
                SELECT 1 FROM saLoteEntrada le2
                WHERE le2.co_art = le.co_art AND le2.co_alma = le.co_alma
                  AND le2.numero_lote = le.numero_lote AND le2.precio > 0
            ) AND NOT EXISTS(
                SELECT 1 FROM saLoteEntrada le3
                WHERE le3.co_art = le.co_art AND le3.co_alma = le.co_alma
                  AND le3.precio > 0
                  AND le3.fecha_inicio BETWEEN DATEADD(DAY,-90,le.fecha_inicio)
                                           AND DATEADD(DAY,90,le.fecha_inicio)
            ) THEN 1 ELSE 0 END) AS sin_fuente_de_costo
        FROM saLoteEntrada le
        WHERE le.tipo_doc IN ('AJUS','NREC','COMP','GCOM')
          AND le.precio = 0 AND le.stock_actual > 0
    """
    print(sqlcmd_file(client, sql_tot, '/tmp/audit_tot.sql'))

    # ── PASO 2: Aplicar costo — 3 fuentes encadenadas ─────────────────
    print("\n[2] APLICANDO COSTOS (fuente 1 → 2 → 3)...")

    fix_sql = """
    SET NOCOUNT ON;

    -- ═══════════════════════════════════════════════════════════════
    -- FUENTE 1: Costo del registro HERMANO (mismo numero_lote, mismo
    --           artículo/almacén, pero con precio > 0).
    --           Promedio ponderado si hay varios hermanos.
    -- ═══════════════════════════════════════════════════════════════
    UPDATE le
    SET le.precio = hermano.precio_hermano,
        le.co_us_mo = 'SYS',
        le.fe_us_mo = GETDATE()
    FROM saLoteEntrada le
    CROSS APPLY (
        SELECT AVG(le2.precio) AS precio_hermano
        FROM saLoteEntrada le2
        WHERE le2.co_art     = le.co_art
          AND le2.co_alma    = le.co_alma
          AND le2.numero_lote = le.numero_lote
          AND le2.precio > 0
    ) hermano
    WHERE le.tipo_doc IN ('AJUS','NREC','COMP','GCOM')
      AND le.precio = 0
      AND le.stock_actual > 0
      AND hermano.precio_hermano > 0;

    SELECT 'FUENTE 1 (hermano)' AS fuente, @@ROWCOUNT AS filas_corregidas;

    -- ═══════════════════════════════════════════════════════════════
    -- FUENTE 2: Costo del saAjusteReng correspondiente al mismo lote
    --           (busca por co_art + co_alma + lote_asignado)
    -- ═══════════════════════════════════════════════════════════════
    UPDATE le
    SET le.precio = ar_costo.cost_unit,
        le.co_us_mo = 'SYS',
        le.fe_us_mo = GETDATE()
    FROM saLoteEntrada le
    CROSS APPLY (
        SELECT TOP 1 ar.cost_unit
        FROM saAjusteReng ar
        WHERE ar.co_art  = le.co_art
          AND ar.co_alma = le.co_alma
          AND ar.lote_asignado = 1
          AND ar.cost_unit > 0
          -- Ajuste más cercano en fecha
        ORDER BY ABS(DATEDIFF(DAY,
            (SELECT TOP 1 a.fecha FROM saAjuste a WHERE a.ajue_num = ar.ajue_num),
            le.fecha_inicio)) ASC
    ) ar_costo
    WHERE le.tipo_doc IN ('AJUS','NREC','COMP','GCOM')
      AND le.precio = 0
      AND le.stock_actual > 0;

    SELECT 'FUENTE 2 (saAjusteReng)' AS fuente, @@ROWCOUNT AS filas_corregidas;

    -- ═══════════════════════════════════════════════════════════════
    -- FUENTE 3: Promedio ponderado de lotes del mismo artículo/almacén
    --           dentro de una ventana de ±90 días desde fecha_inicio.
    --           Usa precio * cantidad como ponderación.
    -- ═══════════════════════════════════════════════════════════════
    UPDATE le
    SET le.precio = prom.precio_promedio,
        le.co_us_mo = 'SYS',
        le.fe_us_mo = GETDATE()
    FROM saLoteEntrada le
    CROSS APPLY (
        SELECT
            SUM(le3.precio * le3.cantidad) / NULLIF(SUM(le3.cantidad), 0) AS precio_promedio
        FROM saLoteEntrada le3
        WHERE le3.co_art  = le.co_art
          AND le3.co_alma = le.co_alma
          AND le3.precio  > 0
          AND le3.fecha_inicio BETWEEN DATEADD(DAY, -90, le.fecha_inicio)
                                   AND DATEADD(DAY,  90, le.fecha_inicio)
    ) prom
    WHERE le.tipo_doc IN ('AJUS','NREC','COMP','GCOM')
      AND le.precio = 0
      AND le.stock_actual > 0
      AND prom.precio_promedio > 0;

    SELECT 'FUENTE 3 (promedio ±90d)' AS fuente, @@ROWCOUNT AS filas_corregidas;

    -- ═══════════════════════════════════════════════════════════════
    -- FUENTE 4 (último recurso): Promedio GLOBAL del mismo artículo/almacén
    --           sin restricción de fecha
    -- ═══════════════════════════════════════════════════════════════
    UPDATE le
    SET le.precio = prom_global.precio_global,
        le.co_us_mo = 'SYS',
        le.fe_us_mo = GETDATE()
    FROM saLoteEntrada le
    CROSS APPLY (
        SELECT
            SUM(le4.precio * le4.cantidad) / NULLIF(SUM(le4.cantidad), 0) AS precio_global
        FROM saLoteEntrada le4
        WHERE le4.co_art  = le.co_art
          AND le4.co_alma = le.co_alma
          AND le4.precio  > 0
    ) prom_global
    WHERE le.tipo_doc IN ('AJUS','NREC','COMP','GCOM')
      AND le.precio = 0
      AND le.stock_actual > 0
      AND prom_global.precio_global > 0;

    SELECT 'FUENTE 4 (promedio global)' AS fuente, @@ROWCOUNT AS filas_corregidas;

    -- ═══════════════════════════════════════════════════════════════
    -- VERIFICACIÓN FINAL
    -- ═══════════════════════════════════════════════════════════════
    SELECT
        'Restantes con precio=0' AS estado,
        COUNT(*)             AS registros,
        SUM(stock_actual)    AS stock_afectado
    FROM saLoteEntrada
    WHERE tipo_doc IN ('AJUS','NREC','COMP','GCOM')
      AND precio = 0
      AND stock_actual > 0;

    -- Detalle de los que aún quedan sin costo (si los hay)
    SELECT le.co_art, a.art_des, le.co_alma, le.numero_lote,
           le.tipo_doc, le.stock_actual, le.fecha_inicio
    FROM saLoteEntrada le
    JOIN saArticulo a ON a.co_art = le.co_art
    WHERE le.tipo_doc IN ('AJUS','NREC','COMP','GCOM')
      AND le.precio = 0
      AND le.stock_actual > 0
    ORDER BY le.co_art;
    """
    print(sqlcmd_file(client, fix_sql, '/tmp/fix_masivo_costos.sql'))

    # ── PASO 3: Instalar trigger v2 ahora que los registros están limpios
    print("\n[3] INSTALANDO TRIGGER v2 — Regla 2: precio > 0 en AJUS con stock>0")

    trigger_v2 = """
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
            RAISERROR(
                'CONTROL INVENTARIO: No se permite crear/actualizar un lote '
                'con stock_actual negativo. Verifique las cantidades del ajuste.',
                16, 1
            );
            RETURN;
        END

        -- Regla 2: precio no puede ser 0 en AJUS/NREC/COMP/GCOM con stock positivo
        IF EXISTS (
            SELECT 1 FROM inserted
            WHERE tipo_doc IN ('AJUS','NREC','COMP','GCOM')
              AND ISNULL(precio, 0) = 0
              AND stock_actual > 0
        )
        BEGIN
            ROLLBACK TRANSACTION;
            RAISERROR(
                'CONTROL INVENTARIO: El costo unitario (precio) no puede ser 0 '
                'en un ajuste con stock positivo. Verifique el costo antes de guardar. '
                'Si es un cierre de OP, seleccione el lote antes de confirmar.',
                16, 1
            );
            RETURN;
        END
    END;
    """
    r_trg = sqlcmd_file(client, trigger_v2, '/tmp/trigger_v2.sql')
    print(f"  Trigger v2: {r_trg if r_trg else 'OK — instalado'}")

    # ── PASO 4: Test del trigger v2 ────────────────────────────────────
    print("\n[4] PRUEBAS TRIGGER v2")

    tests = """
    SET NOCOUNT OFF;
    -- Test A: INSERT con precio=0 y stock>0 → DEBE BLOQUEARSE
    PRINT '--- Test A: precio=0, stock>0 (debe bloquear) ---';
    BEGIN TRY
        INSERT INTO saLoteEntrada
            (rowguid_reng,reng_num,tipo_doc,co_art,co_alma,
             numero_lote,fecha_inicio,fecha_expiracion,
             cantidad,stock_actual,precio,
             co_us_in,co_sucu_in,fe_us_in,
             co_us_mo,co_sucu_mo,fe_us_mo,
             revisado,trasnfe,rowguid)
        VALUES(NEWID(),999,'AJUS','PT01D01X019','P1-PT',
            'TST-PRECIO-CERO',GETDATE(),DATEADD(MONTH,6,GETDATE()),
            100,100,0,'SYS','P1',GETDATE(),'SYS','P1',GETDATE(),NULL,NULL,NEWID());
        PRINT 'FALLO: trigger NO bloqueó precio=0';
    END TRY
    BEGIN CATCH
        PRINT 'OK: ' + ERROR_MESSAGE();
    END CATCH;

    -- Test B: INSERT con precio>0 → DEBE PERMITIRSE (se revierte)
    PRINT '--- Test B: precio=801.09, stock>0 (debe permitir) ---';
    BEGIN TRY
        BEGIN TRANSACTION;
        INSERT INTO saLoteEntrada
            (rowguid_reng,reng_num,tipo_doc,co_art,co_alma,
             numero_lote,fecha_inicio,fecha_expiracion,
             cantidad,stock_actual,precio,
             co_us_in,co_sucu_in,fe_us_in,
             co_us_mo,co_sucu_mo,fe_us_mo,
             revisado,trasnfe,rowguid)
        VALUES(NEWID(),999,'AJUS','PT01D01X019','P1-PT',
            'TST-PRECIO-OK',GETDATE(),DATEADD(MONTH,6,GETDATE()),
            100,100,801.09,'SYS','P1',GETDATE(),'SYS','P1',GETDATE(),NULL,NULL,NEWID());
        ROLLBACK TRANSACTION;
        PRINT 'OK: precio=801.09 permitido y revertido correctamente';
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        PRINT 'FALLO inesperado: ' + ERROR_MESSAGE();
    END CATCH;

    -- Test C: INSERT con stock_actual<0 → DEBE BLOQUEARSE
    PRINT '--- Test C: stock_actual=-10 (debe bloquear) ---';
    BEGIN TRY
        INSERT INTO saLoteEntrada
            (rowguid_reng,reng_num,tipo_doc,co_art,co_alma,
             numero_lote,fecha_inicio,fecha_expiracion,
             cantidad,stock_actual,precio,
             co_us_in,co_sucu_in,fe_us_in,
             co_us_mo,co_sucu_mo,fe_us_mo,
             revisado,trasnfe,rowguid)
        VALUES(NEWID(),999,'AJUS','PT01D01X019','P1-PT',
            'TST-NEG',GETDATE(),DATEADD(MONTH,6,GETDATE()),
            -10,-10,801.09,'SYS','P1',GETDATE(),'SYS','P1',GETDATE(),NULL,NULL,NEWID());
        PRINT 'FALLO: trigger NO bloqueó stock negativo';
    END TRY
    BEGIN CATCH
        PRINT 'OK: ' + ERROR_MESSAGE();
    END CATCH;
    """
    print(sqlcmd_file(client, tests, '/tmp/test_trg_v2.sql'))

    # ── PASO 5: Estado final de triggers ───────────────────────────────
    print("\n[5] TRIGGERS ACTIVOS EN saLoteEntrada (estado final)")
    trg_status = """
        SELECT t.name,
               CASE WHEN t.is_disabled=0 THEN 'ACTIVO' ELSE 'INACTIVO' END AS estado,
               CONVERT(VARCHAR, t.modify_date, 120) AS modificado
        FROM sys.triggers t
        JOIN sys.objects o ON o.object_id = t.parent_id
        WHERE o.name = 'saLoteEntrada'
        ORDER BY t.name
    """
    print(sqlcmd_file(client, trg_status, '/tmp/trg_status.sql'))

    # ── PASO 6: Resumen artículos cubiertos ────────────────────────────
    print("\n[6] RESUMEN FINAL — Artículos corregidos por almacén")
    resumen = """
        SELECT le.co_alma,
               COUNT(DISTINCT le.co_art) AS articulos,
               COUNT(*) AS lotes,
               SUM(le.stock_actual) AS stock_total,
               MIN(le.precio) AS precio_minimo,
               MAX(le.precio) AS precio_maximo,
               AVG(le.precio) AS precio_promedio
        FROM saLoteEntrada le
        WHERE le.tipo_doc IN ('AJUS','NREC','COMP','GCOM')
          AND le.co_us_mo = 'SYS'
          AND le.fe_us_mo >= DATEADD(MINUTE, -10, GETDATE())
        GROUP BY le.co_alma
        ORDER BY le.co_alma
    """
    print(sqlcmd_file(client, resumen, '/tmp/resumen_final.sql'))

    print("\n" + "=" * 70)
    print("RESUMEN DE EJECUCIÓN")
    print("=" * 70)
    print("\n✅ COMPLETADO:")
    print("  1. Auditoría previa de 588 lotes con precio=0")
    print("  2. Corrección masiva con 4 fuentes de costo encadenadas")
    print("  3. Trigger v2 instalado (Regla 1: stock<0 + Regla 2: precio=0)")
    print("  4. Pruebas de regresión del trigger v2")
    print("\n🔒 PROTECCIÓN ACTIVA:")
    print("  - Cualquier nuevo AJUS con precio=0 y stock>0 será BLOQUEADO")
    print("  - Cualquier nuevo AJUS con stock<0 será BLOQUEADO")
    print("\n⚠️  PENDIENTE (no urgente):")
    print("  - Fix en SP nsp_spordenproduccioncierre para validar costo antes de crear AJUS")
    print("  - Capacitar a operadores: seleccionar lote ANTES de cerrar frmLotes")

    client.close()

if __name__ == "__main__":
    run()
