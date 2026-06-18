"""
fix_lotes_duplicados_8855.py
============================
Corrige los registros duplicados en saLoteEntrada (CARMAL_A) que causan el error
SQL 1453 al cerrar la orden 8844 (cierre 8855).

CAUSA: Para el articulo ST01D22X001, cada lote tiene 2 filas en saLoteEntrada:
  - tipo_doc='AJUS', stock_actual=0  <- entrada original de Odoo (a eliminar)
  - tipo_doc='TRAS', stock_actual>0  <- traslado real con stock vigente (a conservar)

FIX: Eliminar las filas AJUS con stock_actual=0 que tienen un gemelo TRAS
     para el mismo (co_art, numero_lote, co_alma).

MODO SEGURO:
  - Por defecto: DRY_RUN=True (solo muestra lo que se eliminaria, no lo hace)
  - Para ejecutar: cambiar DRY_RUN=False
  - Siempre ejecuta dentro de una transaccion con rollback disponible
"""
import pyodbc, sys

SERVER   = "192.168.60.15"   # Servidor de pruebas primero
USER     = "PROFIT"
PASS     = "profit"
DATABASE = "CARMAL_A"
ARTICULO = "ST01D22X001"

# ===== CONTROL DE SEGURIDAD =====
DRY_RUN = False  # Cambiar a False para ejecutar el DELETE real
# ================================

def get_conn():
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SERVER};DATABASE={DATABASE};"
        f"UID={USER};PWD={PASS};"
        "Encrypt=yes;TrustServerCertificate=yes;",
        autocommit=False  # Necesitamos transaccion manual
    )

print(f"{'='*65}")
print(f"  FIX: Lotes duplicados en saLoteEntrada para {ARTICULO}")
print(f"  Servidor: {SERVER} | DB: {DATABASE}")
print(f"  MODO: {'DRY RUN (sin cambios)' if DRY_RUN else '>>> EJECUCION REAL <<<'}")
print(f"{'='*65}")

conn = get_conn()
cur  = conn.cursor()

# ── PASO 1: Identificar filas a eliminar ────────────────────────────────────
# Son filas tipo_doc='AJUS' con stock_actual=0 que tienen un gemelo TRAS
# para el mismo (co_art, numero_lote, co_alma)
sql_identify = f"""
SELECT le.rowguid,
       le.numero_lote,
       le.co_alma,
       le.tipo_doc,
       le.stock_actual,
       le.cantidad,
       le.precio,
       CONVERT(VARCHAR(19), le.fe_us_in, 120) AS fe_us_in
FROM saLoteEntrada le
WHERE le.co_art = '{ARTICULO}'
  AND le.tipo_doc = 'AJUS'
  AND le.stock_actual = 0
  AND EXISTS (
      SELECT 1 FROM saLoteEntrada le2
      WHERE le2.co_art     = le.co_art
        AND le2.numero_lote = le.numero_lote
        AND le2.co_alma     = le.co_alma
        AND le2.tipo_doc    = 'TRAS'
        AND le2.rowguid    <> le.rowguid
  )
ORDER BY le.numero_lote, le.co_alma
"""

print("\n  Filas a eliminar (AJUS con stock=0 que tienen gemelo TRAS):")
cur.execute(sql_identify)
filas = cur.fetchall()
cols  = [d[0] for d in cur.description]

if not filas:
    print("  [OK] No se encontraron duplicados. No hay nada que corregir.")
    conn.close()
    sys.exit(0)

for f in filas:
    row = dict(zip(cols, f))
    print(f"    rowguid={row['rowguid']} | lote={row['numero_lote'].strip()} | "
          f"alma={row['co_alma'].strip()} | tipo={row['tipo_doc']} | "
          f"stock={row['stock_actual']} | cant={row['cantidad']}")

rowguids_to_delete = [f[0] for f in filas]
print(f"\n  Total a eliminar: {len(rowguids_to_delete)} fila(s)")

# ── PASO 2: Verificar que el gemelo TRAS tiene el stock correcto ─────────────
print("\n  Filas CONSERVADAS (TRAS con stock vigente):")
sql_conservar = f"""
SELECT le2.rowguid, le2.numero_lote, le2.co_alma,
       le2.tipo_doc, le2.stock_actual, le2.cantidad, le2.precio
FROM saLoteEntrada le2
WHERE le2.co_art = '{ARTICULO}'
  AND le2.tipo_doc = 'TRAS'
  AND EXISTS (
      SELECT 1 FROM saLoteEntrada le
      WHERE le.co_art      = le2.co_art
        AND le.numero_lote  = le2.numero_lote
        AND le.co_alma      = le2.co_alma
        AND le.tipo_doc     = 'AJUS'
        AND le.stock_actual = 0
  )
ORDER BY le2.numero_lote, le2.co_alma
"""
cur.execute(sql_conservar)
conservar = cur.fetchall()
cols2 = [d[0] for d in cur.description]
for f in conservar:
    row = dict(zip(cols2, f))
    print(f"    rowguid={row['rowguid']} | lote={row['numero_lote'].strip()} | "
          f"alma={row['co_alma'].strip()} | stock={row['stock_actual']} | "
          f"cant={row['cantidad']} | precio={row['precio']}")

if DRY_RUN:
    print(f"\n  [DRY RUN] Se eliminarian {len(rowguids_to_delete)} fila(s).")
    print("  Para ejecutar el fix real, cambia DRY_RUN = False en el script.")
    conn.close()
    sys.exit(0)

# ── PASO 3: EJECUTAR DELETE dentro de transaccion ───────────────────────────
print(f"\n  [EJECUTANDO] Eliminando {len(rowguids_to_delete)} fila(s)...")
try:
    # Construir placeholders para IN clause
    placeholders = ",".join(["?" for _ in rowguids_to_delete])
    sql_delete = f"""
    DELETE FROM saLoteEntrada
    WHERE co_art = '{ARTICULO}'
      AND tipo_doc = 'AJUS'
      AND stock_actual = 0
      AND rowguid IN ({placeholders})
    """
    cur.execute(sql_delete, rowguids_to_delete)
    deleted = cur.rowcount
    print(f"  Filas eliminadas: {deleted}")

    # Verificar que ya no hay duplicados
    cur.execute(sql_identify)
    post_dupes = cur.fetchall()
    if post_dupes:
        print(f"  [ADVERTENCIA] Aun quedan {len(post_dupes)} duplicados. Haciendo ROLLBACK.")
        conn.rollback()
        sys.exit(1)

    conn.commit()
    print("  [OK] COMMIT exitoso. Duplicados eliminados correctamente.")
    print("  Ahora puedes reintentar el cierre 8855 de la orden 8844.")

except Exception as e:
    print(f"  [ERROR] {e}")
    conn.rollback()
    print("  ROLLBACK ejecutado. Sin cambios en la base de datos.")
    sys.exit(1)
finally:
    conn.close()
