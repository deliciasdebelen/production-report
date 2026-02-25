-- ====================================================================================
-- Author:      AntiGravity (Generic AI Assistant)
-- Create date: 2026-01-14
-- Description: Calculates unit breakdown (e.g., Boxes and separate Units) 
--              based on a total quantity for a given article.
--              Uses saArtUnidad to find the equivalency factor.
-- 
-- Execution Example:
-- EXEC sp_calculo_equivalencias_unidades @co_art = 'PT-1001', @total_cantidad = 50
-- ====================================================================================

IF OBJECT_ID('sp_calculo_equivalencias_unidades', 'P') IS NOT NULL
    DROP PROCEDURE sp_calculo_equivalencias_unidades
GO

CREATE PROCEDURE sp_calculo_equivalencias_unidades
    @co_art CHAR(30),
    @total_cantidad DECIMAL(18, 5)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @co_uni_base CHAR(6)
    DECLARE @co_uni_empaque CHAR(6)
    DECLARE @factor_equivalencia DECIMAL(18, 5)
    
    DECLARE @cantidad_empaque DECIMAL(18, 5) -- Cantidad de Cajas/Bultos calculada
    DECLARE @cantidad_restante DECIMAL(18, 5) -- Unidades sueltas restantes

    -- 1. Identificar la Unidad Base (Generalmente equivalencia = 1)
    SELECT TOP 1 @co_uni_base = co_uni
    FROM saArtUnidad
    WHERE co_art = @co_art AND equivalencia = 1

    -- 2. Identificar la Unidad de Empaque Mayor (Donde equivalencia > 1)
    --    Se asume la equivalencia mas alta como la unidad de empaque principal (Ej. Bulto o Caja)
    --    Se puede ajustar para buscar por uso_secundaria = 1 si es preferido
    SELECT TOP 1 
        @co_uni_empaque = co_uni,
        @factor_equivalencia = equivalencia
    FROM saArtUnidad
    WHERE co_art = @co_art AND equivalencia > 1
    ORDER BY equivalencia DESC -- Tomar la jerarquia mas alta

    -- Validacion: Si no hay unidad de empaque, todo es unidad base
    IF @factor_equivalencia IS NULL OR @factor_equivalencia = 0
    BEGIN
        SET @factor_equivalencia = 1
        SET @co_uni_empaque = @co_uni_base
    END

    -- 3. Calcular "Armado"
    -- Cantidad de empaques completos (Division Entera)
    SET @cantidad_empaque = FLOOR(@total_cantidad / @factor_equivalencia)

    -- Cantidad restante (Residuo)
    SET @cantidad_restante = @total_cantidad - (@cantidad_empaque * @factor_equivalencia)

    -- 4. Retornar Resultado
    SELECT 
        @co_art AS co_art,
        @total_cantidad AS cantidad_total,
        @co_uni_empaque AS unidad_empaque,
        @factor_equivalencia AS factor_empaque,
        @cantidad_empaque AS cantidad_bultos_completos,
        @co_uni_base AS unidad_base,
        @cantidad_restante AS cantidad_unidades_sueltas,
        -- Texto descriptivo para UI
        CAST(@cantidad_empaque AS VARCHAR) + ' ' + TRIM(@co_uni_empaque) + ' + ' + 
        CAST(@cantidad_restante AS VARCHAR) + ' ' + TRIM(@co_uni_base) AS descripcion_armado
END
GO
