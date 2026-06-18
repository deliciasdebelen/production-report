import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22
TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"
SQL_DB = "carmal_a"

# ─────────────────────────────────────────────────────────────
# El análisis mostró que RT-01 y RT-02 pasaron porque Profit 
# escribe Rowguid_Lote = rowguid_reng del saLoteSalida mismo,
# no NULL. El INNER JOIN falla, no el NOT EXISTS.
# 
# El problema REAL confirmado en RT-07:
# P1-PS: Sistema dice 29.01, movimientos calculan 689.49
# Diferencia = 660.47 kg de ácido cítrico SIN descontar
# Esto confirma que saLoteSalida tiene registros GCOM
# que NO están siendo considerados en el stock.
#
# La raíz: saStockAlmacen se calcula en tiempo real por Profit
# usando solo movimientos con documentos "confirmados". 
# Los GCOM huérfanos NO se incluyen en ese cálculo.
# ─────────────────────────────────────────────────────────────

SP_RECONCILIAR = """
IF OBJECT_ID('dbo.sp_ReconciliarLotesGCOM') IS NOT NULL
    DROP PROCEDURE dbo.sp_ReconciliarLotesGCOM;
"""

SP_RECONCILIAR_BODY = """
CREATE PROCEDURE [dbo].[sp_ReconciliarLotesGCOM]
    @solo_revision BIT = 1,
    @fecha_desde DATE = NULL
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @fecha_corte DATE;
    SET @fecha_corte = ISNULL(@fecha_desde, '2026-01-01');
    DECLARE @cnt_huerfanos INT;
    DECLARE @cnt_reconciliar INT;

    SELECT 
        ls.rowguid       AS rg_salida,
        ls.co_art,
        ls.co_alma,
        ls.numero_lote,
        ls.cantidad,
        ls.fe_us_in,
        ls.Rowguid_Lote  AS rg_lote_actual
    INTO #GCOMHuerfanos
    FROM saLoteSalida ls
    WHERE ls.tipo_doc = 'GCOM'
      AND ls.fe_us_in >= @fecha_corte
      AND NOT EXISTS (
          SELECT 1 FROM saArtCompuestoGenReng r 
          WHERE r.rowguid = ls.Rowguid_Lote
      );

    SET @cnt_huerfanos = (SELECT COUNT(*) FROM #GCOMHuerfanos);

    SELECT 
        gh.rg_salida,
        gh.co_art,
        gh.co_alma,
        gh.numero_lote,
        gh.cantidad   AS cant_salida,
        gh.fe_us_in,
        r.rowguid     AS rg_renglon_correcto,
        r.gene_num,
        r.reng_num,
        r.total_art   AS cant_renglon,
        r.lote_asignado,
        ABS(r.total_art - gh.cantidad) AS diferencia
    INTO #Reconciliacion
    FROM #GCOMHuerfanos gh
    CROSS APPLY (
        SELECT TOP 1 r.*
        FROM saArtCompuestoGenReng r
        JOIN saArtCompuestoGen g ON g.gene_num = r.gene_num
        WHERE r.co_art = gh.co_art
          AND r.co_alma = gh.co_alma
          AND r.lote_asignado = 0
          AND ABS(r.total_art - gh.cantidad) < 0.05
          AND DATEDIFF(DAY, g.fecha, gh.fe_us_in) BETWEEN -2 AND 2
        ORDER BY ABS(r.total_art - gh.cantidad), g.fecha DESC
    ) r;

    SET @cnt_reconciliar = (SELECT COUNT(*) FROM #Reconciliacion);

    SELECT 
        'REVISION' AS modo,
        CAST(@cnt_huerfanos AS VARCHAR) AS gcom_huerfanos,
        CAST(@cnt_reconciliar AS VARCHAR) AS reconciliaciones_posibles;

    SELECT 
        r.gene_num,
        r.reng_num,
        r.co_art,
        r.numero_lote,
        r.cant_salida,
        r.cant_renglon,
        r.diferencia,
        CONVERT(VARCHAR, r.fe_us_in, 120) AS fecha_salida,
        r.lote_asignado AS estado_actual
    FROM #Reconciliacion r
    ORDER BY r.gene_num, r.reng_num;

    IF @solo_revision = 0
    BEGIN
        BEGIN TRANSACTION;
        BEGIN TRY

            UPDATE ls SET
                ls.Rowguid_Lote = rc.rg_renglon_correcto
            FROM saLoteSalida ls
            JOIN #Reconciliacion rc ON rc.rg_salida = ls.rowguid;

            UPDATE r SET r.lote_asignado = 1
            FROM saArtCompuestoGenReng r
            JOIN #Reconciliacion rc ON rc.rg_renglon_correcto = r.rowguid;

            UPDATE le SET
                le.stock_actual = le.stock_actual - rc.cant_salida
            FROM saLoteEntrada le
            JOIN #Reconciliacion rc 
                ON rc.co_art = le.co_art
               AND rc.co_alma = le.co_alma  
               AND rc.numero_lote = le.numero_lote
            WHERE le.stock_actual >= rc.cant_salida;

            COMMIT TRANSACTION;
            SELECT 'Reconciliacion completada exitosamente' AS resultado;

        END TRY
        BEGIN CATCH
            ROLLBACK TRANSACTION;
            SELECT 'ERROR: ' + ERROR_MESSAGE() AS resultado;
        END CATCH;
    END

    DROP TABLE #GCOMHuerfanos;
    DROP TABLE #Reconciliacion;
END;
"""

TRIGGER_AUTORECONCILIAR = """
IF OBJECT_ID('dbo.trg_AutoReconciliarGCOM') IS NOT NULL
    DROP TRIGGER dbo.trg_AutoReconciliarGCOM;
"""

TRIGGER_AUTORECONCILIAR_BODY = """
CREATE TRIGGER [dbo].[trg_AutoReconciliarGCOM]
ON [dbo].[saLoteSalida]
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    IF NOT EXISTS (SELECT 1 FROM inserted WHERE tipo_doc = 'GCOM')
        RETURN;
    EXEC dbo.sp_ReconciliarLotesGCOM @solo_revision = 0, @fecha_desde = NULL;
END;
"""

def sqlcmd(client, sql, db=SQL_DB):
    clean_sql = sql.replace('"', '\\"')
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -Q "{clean_sql}" 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode(errors='replace').strip()

def sqlcmd_file(client, sql_content, db=SQL_DB):
    """Execute SQL from a file via /tmp"""
    # Write to remote tmp file
    sftp = client.open_sftp()
    with sftp.file('/tmp/fix_gcom.sql', 'w') as f:
        f.write(sql_content)
    sftp.close()
    
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm -v /tmp:/tmp mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -i /tmp/fix_gcom.sql 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    return stdout.read().decode(errors='replace').strip()

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)

    print("=" * 70)
    print("APLICANDO FIX: SP sp_ReconciliarLotesGCOM + Trigger Auto")
    print("=" * 70)

    # 1. DROP existente del SP
    print("\n[1a] Eliminando SP anterior (si existe)...")
    result = sqlcmd_file(client, SP_RECONCILIAR)
    print(result if result else "OK")

    # 2. Crear el SP body
    print("\n[1b] Creando SP sp_ReconciliarLotesGCOM...")
    result2 = sqlcmd_file(client, SP_RECONCILIAR_BODY)
    print(result2 if result2 else "OK")

    # 3. Ejecutar en modo revisión primero (DRY RUN)
    print("\n[2] DRY RUN — revisión sin cambios...")
    result3 = sqlcmd(client, "EXEC dbo.sp_ReconciliarLotesGCOM @solo_revision=1, @fecha_desde='2026-01-01'")
    print(result3)

    # 4. DROP existente del trigger
    print("\n[3a] Eliminando trigger anterior (si existe)...")
    result4 = sqlcmd_file(client, TRIGGER_AUTORECONCILIAR)
    print(result4 if result4 else "OK")

    # 5. Crear el trigger body
    print("\n[3b] Creando Trigger trg_AutoReconciliarGCOM...")
    result5 = sqlcmd_file(client, TRIGGER_AUTORECONCILIAR_BODY)
    print(result5 if result5 else "OK")

    # 6. Verificar objetos instalados
    print("\n[4] Objetos instalados en carmal_a:")
    objs = sqlcmd(client, """
        SELECT o.name, o.type_desc,
               CONVERT(VARCHAR, o.create_date, 120) AS creado
        FROM sys.objects o
        WHERE o.name IN ('sp_ReconciliarLotesGCOM', 'trg_AutoReconciliarGCOM')
        ORDER BY o.name
    """)
    print(objs)

    # 7. Triggers activos
    print("\n[5] Triggers activos post-instalación:")
    trg = sqlcmd(client, """
        SELECT t.name, o.name AS tabla, CASE WHEN t.is_disabled=0 THEN 'ACTIVO' ELSE 'INACTIVO' END AS estado
        FROM sys.triggers t JOIN sys.objects o ON o.object_id = t.parent_id
        WHERE t.name IN ('trg_AutoReconciliarGCOM', 'TrigEstado_saArtCompuestoGen',
                         'ActualizarFechaLote', 'trg_BlockLoteSinExistencia')
    """)
    print(trg)

    print("\n" + "=" * 70)
    print("FIX INSTALADO. Para aplicar a registros históricos ejecutar:")
    print("  EXEC dbo.sp_ReconciliarLotesGCOM @solo_revision=0, @fecha_desde='2026-01-01'")
    print("=" * 70)

    client.close()

if __name__ == "__main__":
    run()

