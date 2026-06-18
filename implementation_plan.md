# Plan de Arquitectura Avanzada: Odoo ↔ Profit Plus (Costos, LDP y Stock)

Según los últimos requerimientos funcionales y el análisis forense de la base de datos `carmal_a`, la integración `carmal_m` tiene una serie de reglas de negocio intrínsecas a Profit Plus que fueron saltadas en la primera versión y que amenazan la viabilidad de la contabilidad de costos. Por consiguiente, se elabora un plan para reescribir e integrar los requerimientos estrictos.

> [!CAUTION]
> He **apagado las automatizaciones de Odoo en producción** y detenido el contenedor `Bridge API` para evitar la creación de más ajustes contables con `Costo = 0.00`, lo cual estaba corrompiendo el inventario general.

## User Review Required

Al usuario: Por favor revisa y confirma los siguientes puntos clave, dado su impacto severo:
1. **Borrado de Datos Actuales:** Mencionaste *"elimina las que estan actualmente en odoo y tambien ordenes"*. ¿Confirma que las recetas (Liastas de Materiales / BoM) y las Órdenes de Manufactura actuales deben truncarse de la base de datos de Odoo?
2. **Sincronización a 5 Segundos:** Una carga HTTP tan frecuente puede generar Locks en SQL Server o saturar el Bridge API. ¿Se podría manejar la sincronización con Webhooks (Instantáneo solo cuando haya cambios) o un periodo ligeramente mayor (ej. 1 minuto)?
3. **Cálculo exacto de Costo:** Se auditaron las tablas; Profit carece de campos convencionales para `stock` directamente en `saArticulo`. Generaré consultas avanzadas buscando las Vistas (Views) o Procedimientos Almacenados (SPs) que Profit usa tras bambalinas para no errarle a los cálculos matemáticos (Suma Total Consumo MP / Und PT).

## Proposed Changes

---
### 1. Refactorización Matemática del Costo (`carmal_m` Parity)

Para imitar a la perfección la inserción de un ajuste de inventario real creado por la manufactura de Profit (`ODP / CIERRE`):

#### [MODIFY] `profit_api/routers/manufacture.py` (Nuevo Router)
-   Implementar llamada a la función/vista de control de inventario de Profit (`vStock` o la que corresponda) para extraer el `$CostoUnitario` a la fecha.
-   **Regla Matemática S-MPR:**
    -   `cost_unit` = Costo Promedio extraído de Profit.
    -   `cost_total` = `cost_unit` * `cantidad`.
-   **Regla Matemática E-PTD:**
    -   `cost_total` = Sumatoria de los `cost_total` de los renglones `S-MPR`.
    -   `cost_unit` = `cost_total` / `cantidad_producida`.

#### [MODIFY] `extra-addons/profit_sync/models/mrp_production_profit.py`
-   Enviar al endpoint vía JSON no solamente las cantidades teóricas, sino las cantidades consumidas con sus lotes correspondientes al dar "Aceptar" a la Orden y generar el cálculo de prorrateo.

---
### 2. Bloqueo de Manufactura sin Disponibilidad Odoo/Profit

La integración bloqueará de raíz las órdenes desde la interfaz local de Odoo si `carmal_a` arroja falta de stock.

#### [MODIFY] `extra-addons/profit_sync/models/mrp_production.py`
-   Sustituir el botón "Confirmar" de Odoo por un método propio que envíe el requerimiento de componentes al API y llame a validación de stock físico con lógica transaccional.
-   Si la respuesta de la API es `InsufficientStockError`, la UI se detiene y muestra una Alerta de Odoo impidiendo avanzar.

---
### 3. Migrador Nativo de Recetas (`saArtCompuestoGen`)

Los Maestros de Manufactura gobernarán desde Profit. 

#### [NEW] `profit_api/routers/sync_bom.py`
-   Servicio que lee `saArtCompuestoGen` (Cabecera de Fórmula) y `saArtCompuestoGenReng` (Líneas de componentes).
-   Cruza los Códigos de Artículo (`co_art`) y empaqueta la jerarquía a lo que Odoo 17 entiende como `mrp.bom` y `mrp.bom.line`.

#### [NEW] `profit_api/services/clean_odoo_data.py`
-   Comando de ejecución única que ejecutará sentencias `SQL DELETE CASCADE` seguras dentro del esquema de Odoo para borrar el inventario espurio de OdMs (órdenes) y de Fórmulas manuales.

---
### 4. Backorders y Entregas Parciales (Ajustes Iterativos)

Para posibilitar "pido 100, cierro 50 y luego 50":
-   **Gestión por Lote de Despacho:** Odoo permite validaciones parciales creando un "Backorder" (Orden Adicional Vinculada).
-   **Sincronización:** Cada vez que el usuario presiona "[Registrar Producción de X Unidades]", la interfaz detectará la porción consumida, notificará a la API y generará su propio `saAjuste`. Si se hace un backorder, la Orden hija originará un documento `saAjuste` secundario al validarse.

## Open Questions

> [!IMPORTANT]
> 1. **Fórmulas Avanzadas:** Si las recetas en Profit incluyen Costos Generales Estándar adicionales (mano de obra u operativos no asociados a un artículo directo, ej. CIF), ¿cómo prefiere que los cargue Odoo? (¿Como un artículo de servicio extra?)
> 2. **Sincronizador Continuo (5s):** Recomiendo usar en Odoo el motor Webhooks directo, de lo contrario un Polling a la DB de Profit Server cada 5 segundos equivaldrá a ~17.280 consultas diarias; ¿Esto es aceptable a nivel de infraestructura para Odoo o para SQL Server?

## Verification Plan

### Automated Tests
- Validaré que el API es capaz de leer la receta nativa de Profit con `pytest`.
- Enviaré mock payloads y validaré que el campo `cost_unit` resultante del cálculo E-PTD iguale exactamente las sumatorias extraídas localmente desde bases de datos controladas.

### Manual Verification
1. Ingresaremos y revisaremos en Odoo la lista de Listas de Materiales, confirmando que coincidan 1-A-1 con el ERP.
2. Confirmaremos una orden falsa para la cual el stock físico se halle en `Cero` para atestiguar que el bloqueo del UI funcione.
3. Emitiremos una Orden para 100 Unds, procesaremos una parcial de 50 Unds, y verificaremos contablemente que Profit registre 1 Documento de Ajuste por la proporcional de Costos.
