# Informe de Inconsistencias de Inventario (Lotes P1-PT)
**Servidor Analizado**: `192.168.1.205 (CARMAL_A)`

Tras ejecutar exitosamente las validaciones locales orientadas a diagnosticar los 12 lotes del almacén **P1-PT** cuyo stock actual es `0.00000` en lugar del valor negativo que se muestra en los flujos matemáticos de manufactura y ajuste, estos son los hallazgos:

## 1. Causa Raíz de las Inconsistencias

### A. Lote Inexistente (`ME260312-03`)
Este lote en particular (`PT01P01X011`) sufre de una causa diferente al resto. **El lote no existe en la tabla maestra `saLoteEntrada`**. Al no tener un registro original de "Entrada" fundacional, el motor de la base de datos no tiene una fila base para restarle o sumar las salidas. Como resultado lógico, en consultas directas y balance, su valor base aparece como cero (`0.00000`).

### B. Bloqueo de Stock Negativo (`CHECK CONSTRAINT`)
Para los 11 lotes restantes (incluyendo `L1260226-01`, `L1 260302-01`, etc.), la causa obedece a una estructura estricta a nivel lógico en Profit Plus:
Actualmente, la tabla `saLoteEntrada` de la base de datos `CARMAL_A` cuenta con la siguiente regla estricta activada: 

```sql
CHECK ([Stock_Actual]>=(0))
```

Esta regla o *Constraint* prohíbe determinadamente a SQL Server grabar valores negativos en este campo bajo ninguna circunstancia. Cuando los procedimientos almacenados (ej. `pActualizarLote` o `pInsertarRenglonesLote`) o los disparadores del sistema procesan un documento de Salida o Ajuste ("AJUS") cuyas líneas exceden la cantidad permitida inicial, si el sistema forzara la resta a (`-24.0`), SQL Server arrojaría un error crítico denegando la factura/ajuste por completo. Para evitar que se congele la facturación/despacho, el valor simplemente queda bloqueado topado en el límite del Check, que es `0.00`.

## 2. Propuestas de Solución

Para solventar esta inconsistencia tienes dos caminos, dependiendo netamente de la lógica de negocio de la empresa:

### Solución Uno: Habilitar el Inventario de Lote Negativo (A nivel BD)
Si en el modelo logístico de **Delicias de Belén** es totalmente imperativo y normal contemplar que un número de lote en tránsito o mal conciliado adquiera saldos en déficit (ej: `-624.00`), se requiere eliminar el candado actual en la Base de Datos.

**Ejecución:** Excluir la regla desde MSSQL Server:
```sql
ALTER TABLE saLoteEntrada DROP CONSTRAINT [Nombre_del_Constraint];
```
*(Luego de hacer esto, los triggers permitirán que los ajustes posteriores pasen la barrera del cero)*.

---

### Solución Dos: Cuadre Operativo o Ajuste de Entrada "AJUE"
En la industria, el saldo de un lote individual no debe ser negativo; un lote material no puede sacar "más existencias" del contenedor de las que alguna vez entraron. Si se asume esta filosofía de integridad clásica de Profit Plus, el stock en `0` es el correcto y el error real es operativo o de los tiempos en la cadena de importación.

**Ejecución:**
1. **Insertar Base de Lote Huérfano `ME260312-03`**: Se debe elaborar un documento `AJUE` del artículo `PT01P01X011` asignándole estrictamente este lote con la cantidad del faltante que originó la inconsistencia o a cero solo para matricularlo y permitir conciliar las Salidas en los Querys.
2. **Normalización por Ajustes Compuestos**: Formular ingresos de mercancía equivalentes al negativo virtual que estás evidenciando, para rellenar ese "agujero" en las tablas de entrada contra las de salida.

> [!NOTE]
> ¿Deseas que preparemos un script SQL formal para **eliminar el Check Constraint** y ver el impacto directo, o prefieres solucionar inyectando ingresos operativos?
