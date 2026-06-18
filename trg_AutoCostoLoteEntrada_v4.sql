-- ============================================================
-- TRIGGER v4: INSTEAD OF INSERT
-- Reemplaza el AFTER INSERT de v3 para evitar el error:
-- "El registro fue modificado por otro usuario"
--
-- CAUSA DEL ERROR:
--   AFTER INSERT trigger hacia UPDATE en el mismo registro
--   → cambiaba la columna validador (timestamp/rowversion)
--   → Profit Plus detectaba el cambio como "otro usuario"
--
-- SOLUCIÓN:
--   INSTEAD OF INSERT intercepta ANTES de insertar.
--   Si precio=0 y stock>0, calcula el costo correcto
--   e inserta directamente con el precio ya corregido.
--   Un solo INSERT → validador se setea una única vez.
--   Profit Plus no ve ningún conflicto de concurrencia.
-- ============================================================

-- Paso 1: Eliminar el trigger AFTER INSERT, UPDATE actual
DROP TRIGGER IF EXISTS [dbo].[trg_BlockAjusteNegativo];
GO

-- Paso 2: Trigger INSTEAD OF INSERT (intercepta antes de insertar)
CREATE TRIGGER [dbo].[trg_AutoCostoLoteEntrada]
ON [dbo].[saLoteEntrada]
INSTEAD OF INSERT
AS
BEGIN
    SET NOCOUNT ON;

    -- Regla 1: Bloquear stock_actual negativo
    IF EXISTS (SELECT 1 FROM inserted WHERE stock_actual < 0)
    BEGIN
        RAISERROR ('CONTROL STOCK: stock_actual no puede ser negativo.', 16, 1);
        RETURN;
    END

    -- Para filas con precio=0 y stock>0 en tipos de entrada:
    -- calcular precio antes de insertar
    -- Para todas las demás: insertar tal como vienen

    INSERT INTO saLoteEntrada (
        rowguid_reng, reng_num, tipo_doc, co_art, co_alma,
        numero_lote, fecha_inicio, fecha_expiracion,
        cantidad, stotal_art, stock_actual, precio,
        costo_adi1, costo_adi2, costo_adi3,
        co_mone, tasa, co_us_in, co_sucu_in, fe_us_in,
        co_us_mo, co_sucu_mo, fe_us_mo,
        revisado, trasnfe, rowguid
    )
    SELECT
        i.rowguid_reng,
        i.reng_num,
        i.tipo_doc,
        i.co_art,
        i.co_alma,
        i.numero_lote,
        i.fecha_inicio,
        i.fecha_expiracion,
        i.cantidad,
        i.stotal_art,
        i.stock_actual,
        -- Precio: si viene en 0 y tiene stock, buscar en fuentes
        CASE
            WHEN i.tipo_doc IN ('AJUS','NREC','COMP','GCOM')
             AND ISNULL(i.precio, 0) = 0
             AND i.stock_actual > 0
            THEN
                COALESCE(
                    -- FUENTE 1: lote hermano (mismo numero_lote con precio>0)
                    (SELECT AVG(le1.precio)
                     FROM saLoteEntrada le1
                     WHERE le1.co_art      = i.co_art
                       AND le1.co_alma     = i.co_alma
                       AND le1.numero_lote = i.numero_lote
                       AND le1.precio      > 0),

                    -- FUENTE 2: saAjusteReng del mismo art/alma con costo>0
                    --           el mas cercano en fecha
                    (SELECT TOP 1 ar.cost_unit
                     FROM saAjusteReng ar
                     JOIN saAjuste a ON a.ajue_num = ar.ajue_num
                     WHERE ar.co_art   = i.co_art
                       AND ar.co_alma  = i.co_alma
                       AND ar.cost_unit > 0
                     ORDER BY ABS(DATEDIFF(DAY, a.fecha, i.fecha_inicio)) ASC),

                    -- FUENTE 3: promedio ponderado ±90 dias mismo art/alma
                    (SELECT SUM(le3.precio * le3.cantidad)
                            / NULLIF(SUM(le3.cantidad), 0)
                     FROM saLoteEntrada le3
                     WHERE le3.co_art  = i.co_art
                       AND le3.co_alma = i.co_alma
                       AND le3.precio  > 0
                       AND le3.fecha_inicio BETWEEN DATEADD(DAY,-90,i.fecha_inicio)
                                                AND DATEADD(DAY, 90,i.fecha_inicio)),

                    -- FUENTE 4: promedio global mismo art/alma
                    (SELECT SUM(le4.precio * le4.cantidad)
                            / NULLIF(SUM(le4.cantidad), 0)
                     FROM saLoteEntrada le4
                     WHERE le4.co_art  = i.co_art
                       AND le4.co_alma = i.co_alma
                       AND le4.precio  > 0),

                    -- FUENTE 5: dejar en 0 si no hay fuente
                    --           (no bloquear — manufactura no puede detenerse)
                    0
                )
            ELSE i.precio
        END,
        i.costo_adi1,
        i.costo_adi2,
        i.costo_adi3,
        i.co_mone,
        i.tasa,
        -- co_us_mo: marcar como 'TRG' solo si el costo fue auto-corregido
        i.co_us_in,
        i.co_sucu_in,
        i.fe_us_in,
        CASE
            WHEN i.tipo_doc IN ('AJUS','NREC','COMP','GCOM')
             AND ISNULL(i.precio, 0) = 0
             AND i.stock_actual > 0
            THEN 'TRG'
            ELSE i.co_us_mo
        END,
        i.co_sucu_mo,
        i.fe_us_mo,
        i.revisado,
        i.trasnfe,
        i.rowguid
    FROM inserted i;

END;
GO

-- Paso 3: Trigger separado AFTER UPDATE solo para Regla 1 (stock negativo en UPDATE)
CREATE TRIGGER [dbo].[trg_BlockStockNegativo]
ON [dbo].[saLoteEntrada]
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (SELECT 1 FROM inserted WHERE stock_actual < 0)
    BEGIN
        ROLLBACK TRANSACTION;
        RAISERROR ('CONTROL STOCK: stock_actual no puede ser negativo.', 16, 1);
        RETURN;
    END
END;
GO
