# Solución Definitiva para las Desviaciones en `reng_neto`

Para evitar de forma permanente que Profit Plus genere diferencias matemáticas en las devoluciones multimoneda (esas diferencias de centímetros causadas por su conversión VES -> USD y viceversa), la forma más directa y contundente es **crear un Trigger de "Limpieza Matemática"**.

Este trigger se ejecuta *una fracción de segundo después* de que Profit guarda el renglón. Su trabajo es ignorar el histórico, ignorar la tasa, e imponer matemáticamente la regla de la compañía al renglón recién insertado, re-actualizando de inmediato la cabecera.

A continuación presento la estructura T-SQL para aplicarlo a tu base de datos (ya sea Producción o Pruebas).

```sql
CREATE TRIGGER [dbo].[TR_AjustarRengNetoDevolucion]
ON [dbo].[saDevolucionClienteReng]
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Ignorar ejecuciones si no hay filas afectadas para prevenir sobrecargas
    IF NOT EXISTS(SELECT * FROM inserted) RETURN;

    -- 1. RECALCULAR RENGLONES A NIVEL MILIMÉTRICO
    -- Forzamos a que el reng_neto sea EXCLUSIVAMENTE (Precio * Cantidad) - Descuento del renglon.
    -- Así eliminamos cualquier "micro-ajuste" insertado previamente por el ejecutable de Profit.
    UPDATE dvr
    SET 
        dvr.reng_neto = (dvr.prec_vta * dvr.total_art) - dvr.monto_desc
    FROM saDevolucionClienteReng dvr
    INNER JOIN inserted i ON dvr.doc_num = i.doc_num AND dvr.reng_num = i.reng_num;

    -- 2. PROPAGAR CÁLCULOS EXACTOS A LA CABECERA (OPCIONAL PERO RECOMENDADO)
    -- Dado que modificamos los totales de los renglones, la cabecera (saDevolucionCliente)
    -- ahora podría estar descuadrada. Re-sumamos todo y corregimos la factura global.
    UPDATE dv
    SET
        dv.total_bruto = res.bruto_exacto,
        dv.total_neto = res.neto_exacto,
        dv.saldo = res.neto_exacto
    FROM saDevolucionCliente dv
    INNER JOIN (
        SELECT 
            doc_num, 
            SUM(total_art * prec_vta) as bruto_exacto,
            SUM(reng_neto) as neto_exacto
        FROM saDevolucionClienteReng
        WHERE doc_num IN (SELECT DISTINCT doc_num FROM inserted)
        GROUP BY doc_num
    ) res ON dv.doc_num = res.doc_num;

END;
```

### Explicación Ejecutiva:
1.  **Diferencia vs el Trigger Viejo:** El trigger viejo intentaba ir a buscar la *Factura Original* y traerse el precio de allá. Eso rompía esquemas. Este trigger nuevo trabaja **únicamente con los datos que ya traía la devolución**, asegurando que sus *propios* números crucen a la perfección matemáticamente.
2.  **Seguridad Contable:** La fórmula impuesta (`(prec_vta * total_art) - monto_desc`) es matemáticamente impecable.
3.  **Corrección en Cascada:** Al final del procedimiento se totaliza toda la devolución (total\_bruto y total\_neto) y se sobreescribe el saldo, anulando por defecto ese error de $+/-$ 1.35$.
