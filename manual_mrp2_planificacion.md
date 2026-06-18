# Manual Paso a Paso: Planificación MRP II
## Módulo `mrp_multi_level` — Odoo 17 Community
**Sistema:** `http://192.168.1.193:8070` · **Fecha:** Abril 2026

---

## CASO DE USO 1: Configurar un Producto para Planificación MRP

### Paso 1 — Buscar el Producto

Ir a: **`Manufactura → Productos → Productos`**

En la barra de búsqueda, escribir el código del producto (ej. `PT01P01X013`) y presionar **Enter**.

![Resultado de búsqueda — Producto PT01P01X013 encontrado](/C:/Users/ovargas/.gemini/antigravity/brain/0c7d0bc6-5065-4aa9-bb6d-424648609be5/.system_generated/click_feedback/click_feedback_1776790652505.png)

El sistema muestra el producto **PIPITA Mayonesa Tradicional PEAD 175g** con código `PT01P01X013`. Hacer clic sobre la tarjeta para abrirlo.

---

### Paso 2 — Verificar Ruta de Fabricación

En la ficha del producto, hacer clic en el tab **`Inventario`**.

![Tab Inventario — Ruta Fabricar activada y menú Más con Áreas MRP](/C:/Users/ovargas/.gemini/antigravity/brain/0c7d0bc6-5065-4aa9-bb6d-424648609be5/.system_generated/click_feedback/click_feedback_1776790680520.png)

> [!IMPORTANT]
> En la sección **Rutas**, verificar que la casilla **"Fabricar"** esté marcada con ✅. Esto es obligatorio para que el MRP genere una **Orden de Fabricación** (y no una Orden de Compra).

En la parte superior derecha también se puede ver el menú **`Más`** con la opción **Áreas MRP** ya visible.

---

### Paso 3 — Acceder a Parámetros MRP del Producto

En la misma ficha del producto, hacer clic en el botón **`Más`** (parte superior derecha) y seleccionar **`Áreas MRP`**.

![Formulario de parámetros MRP — Existencias de Seguridad y Cantidad Mínima configuradas](/C:/Users/ovargas/.gemini/antigravity/brain/0c7d0bc6-5065-4aa9-bb6d-424648609be5/.system_generated/click_feedback/click_feedback_1776790698927.png)

Se abre la pantalla de **Parámetros del Área MRP** para el producto. Los campos clave a completar:

| Campo | Valor en el ejemplo | Descripción |
|---|---|---|
| **Área MRP** | `WH/Stock` | Almacén donde se planifica |
| **Producto** | `PT01P01X013` | Se llena automáticamente |
| **Existencias de seguridad** | `500,00` | Stock mínimo deseado en todo momento |
| **Ctd. Mínima de Pedido** | `1.800,00` | La producción mínima a lanzar |
| **Método de Suministro** | `Producir` | Se determina automáticamente por la ruta |

En la parte inferior, el tab **`Movimientos MRP`** muestra las OdMs existentes de este producto que el motor ya reconoció como **Suministro** actual, evitando sobreplanificar.

Hacer clic en el ícono 💾 (guardar) para confirmar los cambios.

---

## CASO DE USO 2: Ejecutar el Motor MRP

### Paso 4 — Abrir el Asistente MRP

Ir a: **`Manufactura → Planeación → Ejecutar MRP Multi Nivel`**

![Menú Planeación desplegado mostrando todas las opciones MRP](/C:/Users/ovargas/.gemini/antigravity/brain/0c7d0bc6-5065-4aa9-bb6d-424648609be5/.system_generated/click_feedback/click_feedback_1776790713708.png)

El menú **Planeación** contiene todas las herramientas del módulo MRP II:
- **Órdenes Planificadas** — resultado del cálculo
- **Inventario MRP** — vista analítica del stock proyectado
- **Ejecutar MRP Multi Nivel** — dispara el cálculo
- **Generador de fabricaciones** — crea OdMs masivas por fechas

---

### Paso 5 — Ejecutar el Cálculo

Al hacer clic en **"Ejecutar MRP Multi Nivel"** aparece el asistente:

![Asistente "Ejecutar MRP" con área WH/Stock seleccionada](/C:/Users/ovargas/.gemini/antigravity/brain/0c7d0bc6-5065-4aa9-bb6d-424648609be5/.system_generated/click_feedback/click_feedback_1776790725474.png)

1. En **"Áreas MRP a ejecutar"**, verificar que aparece `WH/Stock ×` (ya seleccionada).
2. Hacer clic en el botón **`[Ejecutar MRP]`** (color morado).
3. El sistema procesa todos los productos configurados en esa área.

> [!TIP]
> El cálculo puede tomar algunos segundos. Al finalizar, el asistente se cierra automáticamente y el sistema actualiza el **Inventario MRP**.

---

## CASO DE USO 3: Revisar Resultado y Confirmar Órdenes Planificadas

### Paso 6 — Ver Inventario MRP

Ir a: **`Manufactura → Planeación → Inventario MRP`**

![Inventario MRP — Producto PT04D16X001 con 100 unidades para procurar](/C:/Users/ovargas/.gemini/antigravity/brain/0c7d0bc6-5065-4aa9-bb6d-424648609be5/.system_generated/click_feedback/click_feedback_1776788604958.png)

La lista muestra cada producto planificado con:
- **Stock Inicial:** Stock disponible hoy
- **Demanda:** Necesidades registradas (ventas, previsiones)
- **Para procurar:** ⭐ **La cantidad que el sistema recomienda fabricar o comprar**
- **Método de Suministro:** `Producir` = creará una OdM

---

### Paso 7 — Ver Órdenes Planificadas

Ir a: **`Manufactura → Planeación → Órdenes Planificadas`**

![Lista de Órdenes Planificadas con submenú de Planeación visible](/C:/Users/ovargas/.gemini/antigravity/brain/0c7d0bc6-5065-4aa9-bb6d-424648609be5/.system_generated/click_feedback/click_feedback_1776788635357.png)

Cada fila representa una sugerencia del motor MRP. Las columnas más importantes:

| Columna | Descripción |
|---|---|
| **Área MRP** | Dónde se origina la planificación |
| **Producto** | Artículo a fabricar/comprar |
| **Para procurar** | Cantidad sugerida |
| **Fecha de Lanzamiento** | Cuándo se debe lanzar la orden |
| **Método de Suministro** | Producir / Comprar |

---

### Paso 8 — Confirmar la Orden Planificada

Para convertir la sugerencia en una **Orden de Fabricación real**:

1. Seleccionar la casilla ☑️ de la(s) orden(es) a confirmar.
2. Hacer clic en **`Acción → Ejecutar procura`** (o el ícono ⚙️ de engranaje).
3. Confirmar en el diálogo que aparece.
4. El sistema crea automáticamente la **OdM** en Manufactura.

---

### Paso 9 — Verificar la OdM Generada

Ir a: **`Manufactura → Operaciones → Órdenes de Fabricación`**

![Lista de OdMs — WH/MO/00068 creada automáticamente por MRP con origen "MRP: Existencias de seguridad"](/C:/Users/ovargas/.gemini/antigravity/brain/0c7d0bc6-5065-4aa9-bb6d-424648609be5/.system_generated/click_feedback/click_feedback_1776788655103.png)

La OdM generada por el MRP se distingue porque:
- **Origen:** `MRP: Existencias de seguridad`
- **Estado:** `Confirmada` (lista para producción)
- **Referencia:** Se asigna automáticamente el siguiente número disponible

En el ejemplo, el sistema creó la **OdM WH/MO/00068** por **100 unidades** del producto `PT04D16X001 — Delicias de Belén Mermelada Varietal Fresa 250g`.

---

## CASO DE USO 4: Generador de Fabricaciones por Intervalo de Fecha

### Paso 10 — Abrir el Generador

Ir a: **`Manufactura → Planeación → Generador de fabricaciones`**

Esta herramienta permite crear múltiples OdMs distribuidas en un período de tiempo, ideal para:
- Programar producción semanal durante un mes completo
- Distribuir grandes volúmenes en lotes controlados

### Paso 11 — Configurar el Generador

En el asistente:
1. Seleccionar el **producto** a programar
2. Definir la **Fecha de inicio** y **Fecha de fin** del período
3. Indicar la **frecuencia** (cada cuántos días lanzar una orden)
4. Hacer clic en **`Generar`**

El sistema creará todas las OdMs automáticamente en estado **Borrador**, listas para ser revisadas y confirmadas.

---

## Resumen del Flujo Completo

```
┌─────────────────────────────────────────────────────────┐
│  1. CONFIGURAR                                          │
│     Producto → Más → Áreas MRP                          │
│     Definir: Stock seguridad, Cantidad mínima           │
│                         ↓                               │
│  2. CALCULAR                                            │
│     Planeación → Ejecutar MRP Multi Nivel               │
│     Seleccionar: WH/Stock → [Ejecutar MRP]              │
│                         ↓                               │
│  3. REVISAR                                             │
│     Planeación → Inventario MRP                         │
│     Ver: qué necesita producirse y cuánto               │
│                         ↓                               │
│  4. CONFIRMAR                                           │
│     Planeación → Órdenes Planificadas                   │
│     Seleccionar → Acción → Ejecutar procura             │
│                         ↓                               │
│  5. EJECUTAR                                            │
│     Operaciones → Órdenes de Fabricación                │
│     La OdM aparece con origen "MRP: Existencias..."     │
└─────────────────────────────────────────────────────────┘
```

---

> [!NOTE]
> **Grabación del flujo completo:**  
> Se realizó una grabación de la sesión de pruebas disponible para revisión.

---

*Manual generado el 21 de abril de 2026 · Validado en producción con casos de uso ejecutados en Odoo 17 Community · Servidor 192.168.1.193*
