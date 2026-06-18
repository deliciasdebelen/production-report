ALTER TRIGGER [dbo].[trg_BlockAjusteNegativo]
ON [dbo].[saLoteEntrada]
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    -- REGLA 1: Nunca permitir stock_actual negativo
    IF EXISTS (SELECT 1 FROM inserted WHERE stock_actual < 0)
    BEGIN
        ROLLBACK TRANSACTION;
        RAISERROR ('CONTROL STOCK: stock_actual no puede ser negativo.', 16, 1);
        RETURN;
    END

    -- REGLA 2: Auto-corregir precio=0 en entradas con stock>0
    -- No bloquea — busca el costo y lo asigna automaticamente
    IF EXISTS (
        SELECT 1 FROM inserted
        WHERE tipo_doc IN ('AJUS','NREC','COMP','GCOM')
          AND ISNULL(precio, 0) = 0
          AND stock_actual > 0
    )
    BEGIN
        DECLARE @ACorrregir TABLE (
            rowguid        UNIQUEIDENTIFIER,
            co_art         CHAR(20),
            co_alma        CHAR(20),
            numero_lote    CHAR(20),
            stock_actual   DECIMAL(18,5),
            fecha_inicio   SMALLDATETIME,
            precio_nuevo   DECIMAL(18,5) NULL
        );

        INSERT INTO @ACorrregir (rowguid, co_art, co_alma, numero_lote, stock_actual, fecha_inicio)
        SELECT rowguid, co_art, co_alma, numero_lote, stock_actual, fecha_inicio
        FROM inserted
        WHERE tipo_doc IN ('AJUS','NREC','COMP','GCOM')
          AND ISNULL(precio, 0) = 0
          AND stock_actual > 0;

        -- FUENTE 1: Lote hermano mismo numero_lote con precio>0
        UPDATE ac
        SET ac.precio_nuevo = (
            SELECT AVG(le2.precio)
            FROM saLoteEntrada le2
            WHERE le2.co_art      = ac.co_art
              AND le2.co_alma     = ac.co_alma
              AND le2.numero_lote = ac.numero_lote
              AND le2.precio      > 0
              AND le2.rowguid    <> ac.rowguid
        )
        FROM @ACorrregir ac
        WHERE ac.precio_nuevo IS NULL;

        -- FUENTE 2: saAjusteReng mismo art/alma mas cercano en fecha con costo>0
        UPDATE ac
        SET ac.precio_nuevo = (
            SELECT TOP 1 ar.cost_unit
            FROM saAjusteReng ar
            JOIN saAjuste a ON a.ajue_num = ar.ajue_num
            WHERE ar.co_art   = ac.co_art
              AND ar.co_alma  = ac.co_alma
              AND ar.cost_unit > 0
            ORDER BY ABS(DATEDIFF(DAY, a.fecha, ac.fecha_inicio)) ASC
        )
        FROM @ACorrregir ac
        WHERE ac.precio_nuevo IS NULL;

        -- FUENTE 3: Promedio ponderado lotes mismo art/alma en ventana 90 dias
        UPDATE ac
        SET ac.precio_nuevo = (
            SELECT SUM(le3.precio * le3.cantidad) / NULLIF(SUM(le3.cantidad), 0)
            FROM saLoteEntrada le3
            WHERE le3.co_art   = ac.co_art
              AND le3.co_alma  = ac.co_alma
              AND le3.precio   > 0
              AND le3.fecha_inicio BETWEEN DATEADD(DAY,-90,ac.fecha_inicio)
                                       AND DATEADD(DAY, 90,ac.fecha_inicio)
        )
        FROM @ACorrregir ac
        WHERE ac.precio_nuevo IS NULL;

        -- FUENTE 4: Promedio global mismo art/alma sin limite de fecha
        UPDATE ac
        SET ac.precio_nuevo = (
            SELECT SUM(le4.precio * le4.cantidad) / NULLIF(SUM(le4.cantidad), 0)
            FROM saLoteEntrada le4
            WHERE le4.co_art  = ac.co_art
              AND le4.co_alma = ac.co_alma
              AND le4.precio  > 0
        )
        FROM @ACorrregir ac
        WHERE ac.precio_nuevo IS NULL;

        -- APLICAR el costo encontrado al registro recien creado por carmal_m
        UPDATE le
        SET le.precio   = ac.precio_nuevo,
            le.co_us_mo = 'TRG',
            le.fe_us_mo = GETDATE()
        FROM saLoteEntrada le
        JOIN @ACorrregir ac ON ac.rowguid = le.rowguid
        WHERE ac.precio_nuevo IS NOT NULL
          AND ac.precio_nuevo > 0;

        -- Si quedan sin fuente: se dejan pasar sin bloquear
        -- El proceso de manufactura no puede detenerse
    END
END
