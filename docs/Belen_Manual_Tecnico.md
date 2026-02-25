# Manual Técnico: Supervisor Inteligente "Belén" 👩‍💼

## 1. ¿Qué puede hacer Belén actualmente?
Belén es un sistema experto basado en reglas diseñado para asegurar la integridad de datos entre **Logística (carmal_a)** y **Manufactura (carmal_m)**. A diferencia de un reporte pasivo, Belén **detecta, diagnostica y repara** inconsistencias.

### Habilidades Actuales (Logística - carmal_a):
1.  **Auditoría de Devoluciones (Regla A & B):**
    *   *Detección:* Verifica que `total_neto` en la cabecera coincida con la suma matemática de `bruto + impuestos`.
    *   *Detección:* Verifica que la cabecera coincida con la suma real de los renglones (`saDevolucionClienteReng`).
    *   *Acción:* Recalcula y corrige la cabecera automáticamente.
2.  **Sincronización Devolución ↔ Nota de Crédito (Regla C):**
    *   *Detección:* Compara el monto de la Devolución con su N/CR asociada.
    *   *Acción:* Actualiza la N/CR para que coincida con la devolución real, eliminando "saldos fantasmas".
3.  **Auditoría de Procedimientos (SP Audit):**
    *   *Caso:* `RepMovimientoInventarioxArticuloXlote`.
    *   *Detección:* Identifica JOINs redundantes que duplican inventario.
    *   *Acción:* Se ha optimizado el código SQL en producción.
4.  **Diagnóstico de Warehouses (Almacenes):**
    *   *Detección:* Identifica discrepancias de stock entre tablas de saldo (`saExistencia`) y kardex.

---

## 2. Arquitectura: ¿Cómo "piensa" Belén?
El cerebro de Belén reside principalmente en `app/services/stock_solver.py`.
Su ciclo de pensamiento es:

1.  **Escanear (Get Diagnostics):** Ejecuta consultas SQL optimizadas buscando patrones de error conocidos (WHERE diff > 0.1).
2.  **Reportar (Issues List):** Genera una lista de objetos JSON con `id`, `type`, `severity` y `description`.
3.  **Resolver (Fix Issue):** Recibe un `id` de problema y ejecuta una función específica de SQL (`UPDATE`) para sanear el dato.

---

## 3. ¿Cómo programarle nuevas características?
Para enseñar a Belén sobre nuevos procesos, debes editar `app/services/stock_solver.py`.

### Pasos para agregar una nueva regla:

**A. Definir la Detección (SQL):**
En el método `get_diagnostics`, añade un bloque nuevo:
```python
# Ejemplo: Detectar Facturas sin Transporte
q_check = text("SELECT doc_num, rowguid FROM saFacturaVenta WHERE co_tran IS NULL AND anulado = 0")
results = conn.execute(q_check).fetchall()
for row in results:
    issues.append({
        "type": "MISSING_TRANSPORT",
        "title": f"Factura sin Transporte: {row.doc_num}",
        ...
    })
```

**B. Definir la Solución (Fix):**
En el método `fix_issue`, añade la lógica para manejar ese `type`:
```python
elif issue_type == "MISSING_TRANSPORT":
    # Lógica para asignar transporte por defecto o pedir input
    conn.execute(text("UPDATE saFacturaVenta SET co_tran = '001' WHERE rowguid = :id"), {"id": issue_id})
    return {"success": True, "message": "Transporte asignado."}
```

---

## 4. Integración con Manufactura (carmal_m)
El siguiente paso lógica para Belén es cruzar datos entre **Logística** y **Manufactura**.
Ya tienes configurada la conexión en `app/external_db.py` (`engine_m`).

### Ideas de Implementación:
1.  **Validación de Consumo vs Receta:**
    *   *Objetivo:* Comparar si lo consumido en una Orden de Producción (OP) en `carmal_m` coincide con la "Salida de Producción" en `carmal_a`.
    *   *Consulta:* Unir tablas usando el número de OP como pivote.
2.  **Mermas (Desperdicio):**
    *   Detectar si el % de merma reportado excede el estándar histórico.
3.  **Cierre de Órdenes:**
    *   Alertar si existen OPs "Cerradas" en Manufactura que no han generado su entrada de PT (Producto Terminado) en Logística.

### Ejemplo de Consulta Cruzada:
```python
from app.external_db import engine_m, engine_a

# 1. Obtener OP de Manufactura
op_manufactura = engine_m.execute("SELECT num_orden, cantidad_esperada FROM mpOrdenProduccion WHERE estatus = 'CERRADA'")

# 2. Verificar Entrada en Logística
entrada_logistica = engine_a.execute("SELECT total_art FROM saNotaRecepcion... WHERE doc_orig = :op")
```

---

## 5. El Futuro: Aprendizaje
Actualmente, Belén aprende cuando **tú** codificas una nueva regla basada en un error que descubriste manualmente.
Para hacerla más "autónoma", podemos implementar:
*   **Log de Falsos Positivos:** Si el usuario rechaza una corrección, guardar ese caso para refinar la consulta SQL.
*   **Detección de Anomalías Estadísticas:** En lugar de reglas fijas (`A != B`), usar medias móviles para detectar picos inusuales en costos o inventario (ej. "Esta devolución es 500% mayor al promedio del cliente").
