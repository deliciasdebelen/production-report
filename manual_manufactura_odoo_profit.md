# Manual de Usuario
# Integración Manufactura Odoo 17 → Profit Plus

> **Versión:** 1.0 · **Fecha:** Abril 2026  
> **Sistemas:** Odoo 17 (`192.168.1.193:8070`) · Profit Plus / `carmal_a` (`192.168.60.15`)  
> **Bridge API:** `http://192.168.1.193:8071`

---

## Tabla de Contenido

1. [¿Qué hace esta integración?](#1-qué-hace-esta-integración)
2. [Acceso al Módulo de Manufactura](#2-acceso-al-módulo-de-manufactura)
3. [Paso 1 — Crear una Orden de Manufactura](#3-paso-1--crear-una-orden-de-manufactura)
4. [Paso 2 — Confirmar la OdM (dispara Traslado en Profit)](#4-paso-2--confirmar-la-odm-dispara-traslado-en-profit)
5. [Paso 3 — Durante la Producción](#5-paso-3--durante-la-producción)
6. [Paso 4 — Completar la OdM (dispara Ajuste en Profit)](#6-paso-4--completar-la-odm-dispara-ajuste-en-profit)
7. [Verificar los Documentos en Profit Plus](#7-verificar-los-documentos-en-profit-plus)
8. [Verificar Traslados en Odoo (Inventario)](#8-verificar-traslados-en-odoo-inventario)
9. [Manejo de Lotes](#9-manejo-de-lotes)
10. [Casos Especiales y Comportamiento Esperado](#10-casos-especiales-y-comportamiento-esperado)
11. [Solución de Problemas](#11-solución-de-problemas)
12. [Glosario](#12-glosario)

---

## 1. ¿Qué hace esta integración?

Cuando se trabaja con órdenes de manufactura en Odoo, **el sistema genera automáticamente** los documentos contables correspondientes en Profit Plus sin que el usuario tenga que hacer nada adicional.

El flujo opera en **dos momentos clave**:

```
┌──────────────────────────────────────────────────────────────────┐
│  ODOO                              PROFIT PLUS (carmal_a)        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [CONFIRMAR OdM] ──────────────► saTraslado                      │
│                                   MP: P1-PP → P1-99 → P1-PP1    │
│                                   (reserva el stock de MP)       │
│                                                                  │
│  [COMPLETAR OdM] ──────────────► confirmar saTraslado            │
│                                  + saAjuste                      │
│                                    S-MPR: baja MP de P1-PP       │
│                                    E-PTD: sube PT en P1-PT       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

> [!IMPORTANT]
> **Todo es automático.** El usuario solo trabaja en Odoo como siempre. Profit Plus se sincroniza en segundo plano.

---

## 2. Acceso al Módulo de Manufactura

**URL:** `http://192.168.1.193:8070`

Luego de iniciar sesión, en el menú superior hacer clic en **Manufactura** (o **Fabricación**):

![Lista de Órdenes de Manufactura](C:/Users/ovargas/.gemini/antigravity/brain/0c7d0bc6-5065-4aa9-bb6d-424648609be5/lista_odm_1775565575294.png)

En la vista de lista se pueden ver todas las órdenes con sus estados:

| Estado | Color | Significado |
|--------|-------|-------------|
| **Borrador** | Gris | OdM creada, aún no confirmada |
| **Confirmada** | Azul | Traslado creado en Profit |
| **En progreso** | Naranja | Producción en curso |
| **Hecho** | Verde | Completada y Ajuste enviado a Profit |
| **Cancelada** | Rojo | Anulada |

**Ruta en Odoo:** `Manufactura → Órdenes → Órdenes de Fabricación`

---

## 3. Paso 1 — Crear una Orden de Manufactura

Hacer clic en el botón **`[Nuevo]`** (esquina superior izquierda):

![Nueva Orden de Manufactura](C:/Users/ovargas/.gemini/antigravity/brain/0c7d0bc6-5065-4aa9-bb6d-424648609be5/nueva_odm_1775565603572.png)

Completar los siguientes campos:

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| **Producto** | Producto Terminado a fabricar | `MAYONESA PIPITA GRANEL` |
| **Cantidad** | Unidades a producir | `356` |
| **N° de lote/serie** | Si el PT lleva trazabilidad de lote | `2311171046-02` |
| **Lista de materiales** | Se carga automáticamente desde la receta | *(automático)* |
| **Componentes** | Lista de MP requeridas con cantidades | *(cargados desde receta)* |

> [!NOTE]
> Si el producto tiene una **lista de materiales (BoM)** configurada, los componentes se cargan automáticamente al seleccionar el producto. Si no aparecen, verificar que la BoM esté activa en `Manufactura → Productos → Listas de Materiales`.

---

## 4. Paso 2 — Confirmar la OdM (dispara Traslado en Profit)

Una vez completados los datos, hacer clic en **`[Confirmar]`**:

> [!IMPORTANT]
> Al hacer clic en **Confirmar**, la integración se activa automáticamente:
> 1. La OdM pasa a estado **"Confirmada"**
> 2. El sistema llama al Bridge API → `/api/create_traslado`
> 3. Se crea un **`saTraslado`** en Profit Plus reservando el stock de Materia Prima

**¿Qué pasa en Profit Plus?**

Se crea un documento `saTraslado` con la siguiente ruta de almacenes:

```
P1-PP (Materia Prima) → P1-99 (Tránsito) → P1-PP1 (Línea de Producción)
```

El número del traslado queda guardado en el campo **`Traslado Profit`** del tab `Misceláneo` de la OdM.

---

## 5. Paso 3 — Durante la Producción

La OdM queda en estado **"En progreso"** mientras se ejecuta la producción:

![OdM En Progreso](C:/Users/ovargas/.gemini/antigravity/brain/0c7d0bc6-5065-4aa9-bb6d-424648609be5/odm_en_progreso_v2_1775567432785.png)

Durante esta fase:
- El stock de MP está **reservado** en Profit mediante el traslado (no se ha descontado aún)
- Se puede ver la lista de **componentes** con las cantidades a consumir
- Los operadores ejecutan la producción físicamente

**No se requiere ninguna acción adicional en Profit Plus durante esta etapa.**

---

## 6. Paso 4 — Completar la OdM (dispara Ajuste en Profit)

Una vez terminada la producción, hacer clic en **`[Marcar Como Hecho]`** o completar las cantidades y presionar **`[Validar]`**:

![OdM Completada](C:/Users/ovargas/.gemini/antigravity/brain/0c7d0bc6-5065-4aa9-bb6d-424648609be5/odm_completada_header_1775565739221.png)

Al validar, automáticamente:

1. El `saTraslado` en Profit se **confirma** (`confirma = 1`)
2. Se crea un `saAjuste` con los renglones de consumo y producción:

| Renglón | Tipo | Artículo | Almacén | Efecto |
|---------|------|----------|---------|--------|
| 1 | **E-PTD** | Producto Terminado | `P1-PT` | ↑ Sube stock PT |
| 2 | **S-MPR** | Materia Prima 1 | `P1-PP` | ↓ Baja stock MP |
| 3+ | **S-MPR** | Materia Prima N | `P1-PP` | ↓ Baja stock MP |

### Verificar la sincronización

En el tab **`Misceláneo`** de la OdM ya completada se pueden ver los datos de Profit:

![Campos Profit en Odoo](C:/Users/ovargas/.gemini/antigravity/brain/0c7d0bc6-5065-4aa9-bb6d-424648609be5/odm_campos_profit_1775566952633.png)

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| **Traslado Profit** | Número del `saTraslado` creado en Fase 1 | `0000016674` |
| **Ajuste Profit** | Número del `saAjuste` creado en Fase 2 | `0000008939` |
| **Sincronizado** | Indica si la OdM fue enviada a Profit | `✓` |

---

## 7. Verificar los Documentos en Profit Plus

### Buscar el saTraslado

En Profit Plus → Inventario → Traslados → buscar por número (`0000016674`):

- **alm_orig:** `P1-PP`
- **alm_tmp:** `P1-99`  
- **alm_dest:** `P1-PP1`
- **motivo:** `OdooMO:WH/MO/XXXXX`
- **confirma:** `1` (confirmado al completar la OdM)

**Consulta SQL de verificación:**
```sql
SELECT tras_num, fecha, motivo_glo, alm_orig, alm_dest, confirma
FROM saTraslado
WHERE motivo_glo LIKE 'OdooMO:%'
ORDER BY fecha DESC
```

### Buscar el saAjuste

En Profit Plus → Inventario → Ajustes → buscar por número (`0000008939`):

**Consulta SQL de verificación:**
```sql
SELECT r.reng_num, r.co_tipo,
       LTRIM(RTRIM(r.co_art))  AS articulo,
       r.total_art,
       LTRIM(RTRIM(r.co_uni))  AS unidad,
       LTRIM(RTRIM(r.co_alma)) AS almacen
FROM saAjusteReng r
WHERE LTRIM(RTRIM(r.ajue_num)) = '0000008939'
ORDER BY r.reng_num
```

---

## 8. Verificar Traslados en Odoo (Inventario)

Para ver los movimientos de stock generados en Odoo, ir a:

**`Inventario → Operaciones → Traslados`** → filtrar por tipo **TMAN**

![Traslados TMAN en Odoo](C:/Users/ovargas/.gemini/antigravity/brain/0c7d0bc6-5065-4aa9-bb6d-424648609be5/traslados_tman_1775567352051.png)

El tipo **TMAN** (Traslado Manufactura) registra los movimientos de componentes asociados a cada OdM, permitiendo trazabilidad dentro de Odoo.

---

## 9. Manejo de Lotes

### PT con número de lote

Si el Producto Terminado requiere trazabilidad por lote:

1. Asignar el **número de lote** en la OdM **antes de validar**
2. El sistema marca el renglón `E-PTD` con `lote_asignado = 1`
3. El lote queda asociado al ajuste en Profit

**¿Dónde ingresar el lote?**  
En el formulario de la OdM, campo **"N° de lote/serie"** (parte superior del formulario, a la derecha de la cantidad).

### MP con lote

Si las Materias Primas tienen lotes asignados en Odoo:

| Situación | Comportamiento |
|-----------|---------------|
| Lote de MP **existe** en Profit (`saLoteEntrada`) | Se crea `saLoteSalida` automáticamente |
| Lote de MP **no existe** en Profit | Se omite `saLoteSalida` (sin error) — Warning en log |
| MP **sin lote** | No se crea `saLoteSalida` |
| PT **sin lote** | No se intenta insertar en `saLoteEntrada` |

### Tabla de escenarios completa

| Escenario | PT lot | MP lot | saAjuste | saLoteSalida |
|-----------|--------|--------|----------|:------------:|
| Sin lotes | ✗ | ✗ | ✅ creado | ✗ |
| Solo PT con lote | ✓ | ✗ | ✅ creado | ✗ |
| MP con lote existente | ✗ | ✓ existe | ✅ creado | ✅ |
| MP con lote inexistente | ✗ | ✓ no existe | ✅ creado | ⚠️ omitido |

---

## 10. Casos Especiales y Comportamiento Esperado

### OdM que produce el mismo artículo en mismo almacén

El sistema detecta automáticamente cuando el almacén de origen y destino del traslado coincidirían, y usa **`P1-PP1`** como destino del traslado para cumplir la restricción de Profit (`alm_orig ≠ alm_dest`). No requiere acción del usuario.

### OdM validada más de una vez

Si se valida una OdM que ya fue sincronizada (ya tiene `Ajuste Profit` asignado), el sistema **crea un nuevo ajuste** con número diferente. Cada validación genera un nuevo documento en Profit.

> [!WARNING]
> Evitar cancelar y re-validar OdMs sin coordinación con el área de inventario en Profit Plus, ya que cada validación genera un nuevo `saAjuste`.

### Componente sin unidad de medida configurada

Si un artículo MP no tiene la unidad principal (`uni_principal = 1`) en `saArtUnidad`, el sistema usa `KGS` por defecto y registra una advertencia. El ajuste se crea normalmente.

---

## 11. Solución de Problemas

### El tab "Misceláneo" no muestra los campos Profit

**Causa:** El módulo `profit_sync` no está instalado o actualizado.  
**Solución:** Contactar al administrador del sistema para actualizar el addon.

### La OdM se confirma pero no aparece el número de traslado

**Pasos para verificar:**

1. Verificar que el Bridge API esté activo:
   ```
   http://192.168.1.193:8071/health
   ```
   Debe responder `{"status": "ok"}`

2. En Odoo: `Configuración → Técnico → Automatización` → verificar que estas dos reglas estén **activas**:
   - `Profit Sync: MO Confirmada → Traslado`
   - `Profit Sync: MO Completada → Ajuste Inventario`

3. Revisar el log del Bridge API en el servidor:
   ```bash
   tail -50 /tmp/bridge_8071.log
   ```

### Error visible en el Chatter de la OdM

Si el Chatter muestra un error de sincronización, los datos más comunes son:

| Error | Causa | Solución |
|-------|-------|----------|
| `Connection refused :8071` | Bridge API apagado | Reiniciar el servicio |
| `alm_orig = alm_dest` | Config de almacenes | Verificar configuración |
| `co_uni not found` | MP sin unidad en Profit | Configurar unidad en `saArtUnidad` |
| `CK_saLoteEntrada_TipoDoc` | Permisos usuario PROFIT | Contactar DBA de Profit |

### Consultas útiles en Profit Plus

**Ver todos los traslados generados desde Odoo:**
```sql
SELECT TOP 20 tras_num, fecha, motivo_glo, alm_orig, alm_dest, confirma
FROM saTraslado
WHERE motivo_glo LIKE 'OdooMO:%'
ORDER BY fecha DESC
```

**Ver todos los ajustes generados desde Odoo:**
```sql
SELECT TOP 20 ajue_num, fecha, motivo
FROM saAjuste  
WHERE motivo LIKE 'OdooMO:%'
ORDER BY fecha DESC
```

**Ver el detalle de un ajuste específico:**
```sql
SELECT reng_num, co_tipo, LTRIM(RTRIM(co_art)) art, total_art,
       LTRIM(RTRIM(co_uni)) uni, LTRIM(RTRIM(co_alma)) alma
FROM saAjusteReng
WHERE LTRIM(RTRIM(ajue_num)) = '0000008939'  -- cambiar por el número real
ORDER BY reng_num
```

---

## 12. Glosario

| Término | Significado |
|---------|-------------|
| **OdM** | Orden de Manufactura en Odoo |
| **PT** | Producto Terminado — el artículo que se produce |
| **MP** | Materia Prima — los componentes que se consumen |
| **saTraslado** | Documento de traslado físico en Profit Plus |
| **saTrasladoReng** | Renglones (líneas) del saTraslado |
| **saAjuste** | Documento de ajuste de inventario en Profit Plus |
| **saAjusteReng** | Renglones del saAjuste |
| **E-PTD** | Tipo de ajuste: **Entrada de Producto Terminado** (sube stock PT) |
| **S-MPR** | Tipo de ajuste: **Salida de Materia Prima** (baja stock MP) |
| **saLoteEntrada** | Registro de entrada de lote en Profit (trazabilidad) |
| **saLoteSalida** | Registro de salida de lote en Profit (trazabilidad) |
| **saArtUnidad** | Tabla de unidades de medida de artículos en Profit |
| **P1-PP** | Almacén de Materia Prima |
| **P1-PP1** | Línea de producción (destino del traslado) |
| **P1-99** | Almacén de tránsito temporal |
| **P1-PT** | Almacén de Producto Terminado |
| **Bridge API** | Servicio REST (FastAPI) en puerto `8071` que conecta Odoo con SQL Server |
| **TMAN** | Tipo de operación de picking en Odoo para movimientos de manufactura |
| **lote_asignado** | Campo en `saAjusteReng` que indica si el renglón tiene trazabilidad de lote |
| **x_profit_synced** | Campo personalizado en Odoo indicando sincronización exitosa con Profit |

---

## Arquitectura del Sistema

```
┌──────────────────────────────────────────────────────────────────┐
│  ODOO 17 Community · Docker · 192.168.1.193:8070                 │
│                                                                  │
│  mrp.production (OdM)                                            │
│    ├─ x_profit_tras_num   → Número de saTraslado                 │
│    ├─ x_profit_ajuste_num → Número de saAjuste                   │
│    └─ x_profit_synced     → Estado de sincronización             │
│                                                                  │
│  ir.base_automation (automatizaciones)                           │
│    ├─ "MO Confirmada → Traslado"   → POST /api/create_traslado   │
│    └─ "MO Completada → Ajuste"     → POST /api/sync_production   │
└───────────────────────────┬──────────────────────────────────────┘
                            │ HTTP (JSON)
            ┌───────────────▼────────────────┐
            │  Bridge API · FastAPI · :8071  │
            │                               │
            │  /api/create_traslado         │
            │  /api/confirm_traslado        │
            │  /api/sync_production         │
            └───────────────┬───────────────┘
                            │ pyodbc / ODBC Driver 17
            ┌───────────────▼────────────────┐
            │  SQL Server · 192.168.60.15    │
            │  Base de datos: carmal_a       │
            │  Usuario: PROFIT               │
            │                               │
            │  saTraslado / saTrasladoReng   │
            │  saAjuste  / saAjusteReng      │
            │  saArtUnidad                   │
            │  saLoteEntrada / saLoteSalida  │
            └────────────────────────────────┘
```

---

*Manual generado el 7 de abril de 2026 · Validado con suite de pruebas 48/48 (100%)*
