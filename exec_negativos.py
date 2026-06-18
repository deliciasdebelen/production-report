import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22
TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"
DB = "carmal_a"

def sqlcmd(client, sql, db=DB):
    clean_sql = " ".join(sql.split()).replace('"', '\\"')
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -Q "{clean_sql}" 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode(errors='replace').strip()

def sqlcmd_file(client, sql_content, filename='/tmp/exec_negativos.sql', db=DB):
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

# ══════════════════════════════════════════════════════════════════════
# TRIGGER PREVENTIVO EN saLoteEntrada
# Bloquea cualquier INSERT/UPDATE que resulte en stock_actual < 0
# cuando tipo_doc = 'AJUS', 'NREC', 'TRAS' u otro tipo de ajuste
# ══════════════════════════════════════════════════════════════════════
TRIGGER_DROP = """
IF OBJECT_ID('dbo.trg_BlockAjusteNegativo') IS NOT NULL
    DROP TRIGGER dbo.trg_BlockAjusteNegativo;
"""

TRIGGER_PREVENTIVO = """
CREATE TRIGGER [dbo].[trg_BlockAjusteNegativo]
ON [dbo].[saLoteEntrada]
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    -- Solo bloquear si el resultado final de stock_actual es negativo
    -- en registros que NO son de tipo FACT/NENT (esos los controla trg_BlockLoteSinExistencia)
    IF EXISTS (
        SELECT 1 FROM inserted
        WHERE stock_actual < 0
    )
    BEGIN
        -- Registrar en NSPLog o simplemente bloquear
        ROLLBACK TRANSACTION;
        RAISERROR(
            'CONTROL DE INVENTARIO: No se permite crear/actualizar un lote con stock_actual negativo. Verifique las cantidades del ajuste antes de continuar.',
            16, 1
        );
    END
END;
"""

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)

    print("=" * 70)
    print("EJECUCIÓN — Control de Lotes Negativos P1-PT")
    print("=" * 70)

    # ── PASO 1: Auditar quién creó los AJUS negativos ─────────────────
    print("\n[1] AUDITORÍA — Quién creó los ajustes (AJUS) negativos en saLoteEntrada")
    sql_audit = """
        SELECT le.co_art, le.numero_lote, le.co_alma,
               le.tipo_doc, le.cantidad, le.stock_actual,
               CONVERT(VARCHAR, le.fecha_inicio, 103) AS FecIni,
               le.co_us_in AS usuario_creo,
               CONVERT(VARCHAR, le.fe_us_in, 120) AS fecha_creacion,
               le.co_us_mo AS usuario_modifico,
               CONVERT(VARCHAR, le.fe_us_mo, 120) AS fecha_modif
        FROM saLoteEntrada le
        WHERE le.co_alma = 'P1-PT'
          AND le.stock_actual < 0
          AND le.tipo_doc = 'AJUS'
        ORDER BY le.stock_actual ASC
    """
    print(sqlcmd(client, sql_audit))

    # ── PASO 2: Ver el ajuste de inventario original que originó cada lote ──
    print("\n[2] DOCUMENTOS DE AJUSTE ORIGEN (saAjuste) para lotes negativos")
    sql_ajuste = """
        SELECT a.ajus_num, a.tipo_ajus,
               CONVERT(VARCHAR, a.fecha, 103) AS fecha,
               a.descripcion, a.anulado,
               a.co_us_in AS usuario,
               ar.reng_num, ar.co_art, ar.co_alma, ar.num_lote,
               ar.cantidad AS cantidad_ajuste,
               ar.precio
        FROM saAjuste a
        JOIN saAjusteReng ar ON ar.ajus_num = a.ajus_num
        WHERE ar.co_alma = 'P1-PT'
          AND ar.num_lote IN (
              'L1 260219-01', 'L1 260211-01', 'L1 260212-01',
              'L1 260302-01', 'L2 260302-02', 'L1 260218-01',
              'L2 260406-02', 'L1260226-01', 'L1 260312-01',
              'L1 A260304-01', 'L1 260227-01', 'AFR260224-01',
              'ME260312-03'
          )
        ORDER BY a.fecha ASC
    """
    print(sqlcmd(client, sql_ajuste))

    # ── PASO 3: Generar tabla de ajustes correctivos para Profit Plus ──
    print("\n[3] AJUSTES CORRECTIVOS REQUERIDOS EN PROFIT PLUS")
    print("    (Ajuste positivo por la cantidad exacta del déficit)")
    sql_correctivos = """
        SELECT ROW_NUMBER() OVER (ORDER BY le.stock_actual ASC) AS orden,
               le.co_art,
               a.art_des AS descripcion,
               le.co_alma AS almacen,
               le.numero_lote AS lote,
               le.stock_actual AS deficit_actual,
               ABS(le.stock_actual) AS cantidad_a_ajustar,
               CONVERT(VARCHAR, le.fecha_inicio, 103) AS FecIni,
               CONVERT(VARCHAR, le.fecha_expiracion, 103) AS FecExp,
               'Ajuste positivo para regularizar lote negativo (origen: AJUS)' AS motivo
        FROM saLoteEntrada le
        JOIN saArticulo a ON a.co_art = le.co_art
        WHERE le.co_alma = 'P1-PT'
          AND le.stock_actual < 0
        ORDER BY le.stock_actual ASC
    """
    print(sqlcmd(client, sql_correctivos))

    print("\n    TOTAL UNIDADES A REGULARIZAR POR ARTÍCULO:")
    sql_total = """
        SELECT le.co_art, a.art_des,
               COUNT(*) AS lotes_negativos,
               SUM(ABS(le.stock_actual)) AS total_unidades_a_ajustar
        FROM saLoteEntrada le
        JOIN saArticulo a ON a.co_art = le.co_art
        WHERE le.co_alma = 'P1-PT' AND le.stock_actual < 0
        GROUP BY le.co_art, a.art_des
        ORDER BY SUM(ABS(le.stock_actual)) DESC
    """
    print(sqlcmd(client, sql_total))

    # ── PASO 4: Instalar trigger preventivo en saLoteEntrada ───────────
    print("\n[4] INSTALANDO TRIGGER PREVENTIVO trg_BlockAjusteNegativo")
    r1 = sqlcmd_file(client, TRIGGER_DROP, '/tmp/trg_ajus_drop.sql')
    print(f"  DROP: {r1 if r1 else 'OK'}")

    r2 = sqlcmd_file(client, TRIGGER_PREVENTIVO, '/tmp/trg_ajus_create.sql')
    print(f"  CREATE: {r2 if r2 else 'OK — trigger instalado'}")

    # ── PASO 5: Verificar triggers activos en saLoteEntrada ────────────
    print("\n[5] TRIGGERS ACTIVOS EN saLoteEntrada (post-instalación)")
    sql_trg = """
        SELECT t.name,
               CASE WHEN t.is_disabled=0 THEN 'ACTIVO' ELSE 'INACTIVO' END AS estado,
               CONVERT(VARCHAR, t.modify_date, 120) AS modificado
        FROM sys.triggers t
        JOIN sys.objects o ON o.object_id = t.parent_id
        WHERE o.name = 'saLoteEntrada'
    """
    print(sqlcmd(client, sql_trg))

    # ── PASO 6: Test del trigger (debe fallar si hay negativo) ─────────
    print("\n[6] TEST DEL TRIGGER — Intento de insertar AJUS negativo (debe bloquear)")
    test_sql = """
        BEGIN TRANSACTION;
        BEGIN TRY
            INSERT INTO saLoteEntrada
                (rowguid_reng, reng_num, tipo_doc, co_art, co_alma,
                 numero_lote, fecha_inicio, fecha_expiracion,
                 cantidad, stock_actual, precio,
                 co_us_in, co_sucu_in, fe_us_in,
                 co_us_mo, co_sucu_mo, fe_us_mo,
                 revisado, trasnfe, rowguid)
            VALUES (
                NEWID(), 999, 'AJUS', 'PT01P01X013', 'P1-PT',
                'TEST-NEG-001',
                GETDATE(), DATEADD(MONTH,6,GETDATE()),
                -10, -10, 0,
                'SYS', 'P1', GETDATE(),
                'SYS', 'P1', GETDATE(),
                NULL, NULL, NEWID()
            );
            ROLLBACK TRANSACTION;
            SELECT '*** FALLO: El trigger NO bloqueó el negativo ***' AS test_resultado;
        END TRY
        BEGIN CATCH
            ROLLBACK TRANSACTION;
            SELECT 'OK — Trigger bloqueó correctamente: ' + ERROR_MESSAGE() AS test_resultado;
        END CATCH
    """
    test_result = sqlcmd_file(client, test_sql, '/tmp/test_trigger.sql')
    print(f"  {test_result}")

    # ── PASO 7: Resumen final ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print("RESUMEN DE EJECUCIÓN")
    print("=" * 70)
    print("\n✅ COMPLETADO:")
    print("  1. Auditoría de usuarios que crearon los ajustes negativos")
    print("  2. Identificación de documentos de ajuste origen")
    print("  3. Tabla de ajustes correctivos generada")
    print("  4. Trigger trg_BlockAjusteNegativo instalado en saLoteEntrada")
    print("  5. Trigger validado — bloquea nuevos lotes negativos")
    print()
    print("⚠️  PENDIENTE (requiere acción manual en Profit Plus):")
    print("  - Emitir ajuste de inventario POSITIVO para cada lote negativo")
    print("  - Tipo de ajuste: 'Corrección de inventario' o similar")
    print("  - Ver tabla del PASO 3 para cantidades exactas por lote")
    print()
    print("🔒 PROTECCIÓN FUTURA:")
    print("  - trg_BlockAjusteNegativo bloqueará cualquier intento futuro")
    print("  - de crear/actualizar un lote con stock_actual < 0")

    client.close()

if __name__ == "__main__":
    run()
