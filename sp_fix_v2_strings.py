SP_FIX_V2 = """
IF OBJECT_ID('dbo.sp_ReconciliarLotesGCOM') IS NOT NULL
    DROP PROCEDURE dbo.sp_ReconciliarLotesGCOM;
"""

SP_FIX_V2_BODY = """
CREATE PROCEDURE [dbo].[sp_ReconciliarLotesGCOM]
    @solo_revision BIT = 1,
    @fecha_desde DATE = NULL
AS
BEGIN
    SET NOCOUNT ON;
    --
    -- DISEÑO CORREGIDO (v3):
    -- FK: saLoteSalida.Rowguid_Lote -> saLoteEntrada.rowguid  (correcta, no se toca)
    -- VINCULO ROTO: saLoteSalida.rowguid_reng DEBERIA apuntar a saArtCompuestoGenReng.rowguid
    -- El bug: Profit escribe en rowguid_reng un GUID que NO existe en saArtCompuestoGenReng
    -- Evidencia: saLoteSalida.rowguid_reng = {09490730...} no en saArtCompuestoGenReng
    --
    -- La correccion: Actualizar saLoteSalida.rowguid_reng al rowguid correcto
    -- del renglon de saArtCompuestoGenReng (mismo co_art, co_alma, fecha cercana)
    -- Y luego marcar lote_asignado = 1 en ese renglon
    --

    DECLARE @fecha_corte DATE;
    SET @fecha_corte = ISNULL(@fecha_desde, '2026-01-01');

    -- ====================================================================
    -- PASO 1: GCOMs cuyo rowguid_reng NO existe en saArtCompuestoGenReng
    -- ====================================================================
    SELECT
        ls.rowguid      AS rg_salida,
        ls.rowguid_reng AS rg_reng_actual,
        ls.co_art,
        ls.co_alma,
        ls.numero_lote,
        ls.cantidad,
        ls.fe_us_in,
        ls.Rowguid_Lote AS rg_lote_entrada  -- este esta bien, apunta a saLoteEntrada
    INTO #GCOMHuerfanos
    FROM saLoteSalida ls
    WHERE ls.tipo_doc = 'GCOM'
      AND ls.fe_us_in >= @fecha_corte
      AND NOT EXISTS (
          SELECT 1 FROM saArtCompuestoGenReng r
          WHERE r.rowguid = ls.rowguid_reng
      );

    -- ====================================================================
    -- PASO 2: Buscar el renglon correcto en saArtCompuestoGenReng
    -- Match: mismo co_art + co_alma + total_art >= cant_salida + fecha cercana
    -- ====================================================================
    SELECT
        gh.rg_salida,
        gh.rg_reng_actual,
        gh.co_art,
        gh.co_alma,
        gh.numero_lote,
        gh.cantidad     AS cant_salida,
        gh.fe_us_in,
        gh.rg_lote_entrada,
        r.rowguid       AS rg_renglon_correcto,
        r.gene_num,
        r.reng_num,
        r.total_art     AS cant_renglon_total,
        r.lote_asignado AS lote_asignado_actual
    INTO #Reconciliacion
    FROM #GCOMHuerfanos gh
    CROSS APPLY (
        SELECT TOP 1 r.*
        FROM saArtCompuestoGenReng r
        JOIN saArtCompuestoGen g ON g.gene_num = r.gene_num
        WHERE r.co_art  = gh.co_art
          AND r.co_alma = gh.co_alma
          AND r.total_art >= gh.cantidad
          AND DATEDIFF(DAY, g.fecha, gh.fe_us_in) BETWEEN 0 AND 1
        ORDER BY ABS(DATEDIFF(HOUR, g.fecha, gh.fe_us_in)), g.fecha DESC
    ) r;

    -- Mostrar resumen
    SELECT
        'REVISION'                                                AS modo,
        CAST((SELECT COUNT(*) FROM #GCOMHuerfanos) AS VARCHAR)   AS gcom_huerfanos,
        CAST((SELECT COUNT(*) FROM #Reconciliacion) AS VARCHAR)  AS reconciliaciones_posibles;

    SELECT
        rc.gene_num,
        rc.reng_num,
        rc.co_art,
        rc.numero_lote,
        rc.cant_salida,
        rc.cant_renglon_total,
        rc.lote_asignado_actual,
        CONVERT(VARCHAR, rc.fe_us_in, 120) AS fecha_gcom
    FROM #Reconciliacion rc
    ORDER BY rc.gene_num, rc.reng_num;

    -- ====================================================================
    -- PASO 3: Aplicar si @solo_revision = 0
    -- ====================================================================
    IF @solo_revision = 0
    BEGIN
        BEGIN TRANSACTION;
        BEGIN TRY

            -- 3a. Corregir rowguid_reng en saLoteSalida (restaurar vinculo roto)
            UPDATE ls SET ls.rowguid_reng = rc.rg_renglon_correcto
            FROM saLoteSalida ls
            JOIN #Reconciliacion rc ON rc.rg_salida = ls.rowguid;

            -- 3b. Marcar lote_asignado = 1 en los renglones reconciliados
            UPDATE r SET r.lote_asignado = 1
            FROM saArtCompuestoGenReng r
            JOIN #Reconciliacion rc ON rc.rg_renglon_correcto = r.rowguid;

            -- 3c. Decrementar stock_actual en saLoteEntrada
            -- Usar rg_lote_entrada para identificar el registro exacto
            UPDATE le SET le.stock_actual = le.stock_actual - rc.cant_salida
            FROM saLoteEntrada le
            JOIN #Reconciliacion rc ON rc.rg_lote_entrada = le.rowguid
            WHERE le.stock_actual >= rc.cant_salida;

            COMMIT TRANSACTION;
            SELECT 'OK - Reconciliacion completada exitosamente' AS resultado;

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
