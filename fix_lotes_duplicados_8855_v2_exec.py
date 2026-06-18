"""
fix_lotes_duplicados_8855_v2.py
=================================
Fix alternativo: En lugar de eliminar las filas AJUS duplicadas (que tienen FK en saLoteSalida),
actualizar su numero_lote para hacerlas unicas y que no interfieran con las
subconsultas escalares que buscan por (co_art, numero_lote, co_alma).

ESTRATEGIA: Las filas AJUS con stock_actual=0 que tienen un gemelo TRAS para el
mismo (co_art, numero_lote, co_alma) se les cambia el numero_lote agregando sufijo '-ORIG'.
Esto las saca de las busquedas de lotes activos sin borrarlas.

ALTERNATIVA MAS SEGURA: Verificar si algun SP de Profit busca por numero_lote
y si el cambio no afecta los calculos de costo.

MODO SEGURO: DRY_RUN=True por defecto.
"""
import pyodbc, sys

SERVER   = "192.168.1.205"   # Produccion
USER     = "PROFIT"
PASS     = "profit"
DATABASE = "CARMAL_A"
ARTICULO = "ST01D22X001"

DRY_RUN = False  # Cambiar a False para ejecutar

def get_conn():
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SERVER};DATABASE={DATABASE};"
        f"UID={USER};PWD={PASS};"
        "Encrypt=yes;TrustServerCertificate=yes;",
        autocommit=False
    )

print(f"{'='*65}")
print(f"  FIX v2: Renombrar lotes AJUS duplicados en saLoteEntrada")
print(f"  Servidor: {SERVER} | DB: {DATABASE}")
print(f"  Articulo: {ARTICULO}")
print(f"  MODO: {'DRY RUN (sin cambios)' if DRY_RUN else '>>> EJECUCION REAL <<<'}")
print(f"{'='*65}")

conn = get_conn()
cur  = conn.cursor()

# Identificar filas AJUS con gemelo TRAS (duplicados que causan el error)
sql_dup = f"""
SELECT le.rowguid, le.numero_lote, le.co_alma, le.tipo_doc,
       le.stock_actual, le.cantidad,
       CONVERT(VARCHAR(19), le.fe_us_in, 120) AS fe_us_in
FROM saLoteEntrada le
WHERE le.co_art = '{ARTICULO}'
  AND le.tipo_doc = 'AJUS'
  AND le.stock_actual = 0
  AND EXISTS (
      SELECT 1 FROM saLoteEntrada le2
      WHERE le2.co_art      = le.co_art
        AND le2.numero_lote = le.numero_lote
        AND le2.co_alma     = le.co_alma
        AND le2.tipo_doc    = 'TRAS'
  )
ORDER BY le.numero_lote, le.co_alma
"""

cur.execute(sql_dup)
filas = cur.fetchall()
cols  = [d[0] for d in cur.description]

print(f"\nFilas AJUS duplicadas a renombrar (se les agregara sufijo '-ORI'):")
for f in filas:
    row = dict(zip(cols, f))
    lote_nuevo = (row['numero_lote'].strip() + '-ORI').ljust(20)[:20]
    print(f"  rowguid={row['rowguid']} | lote={row['numero_lote'].strip()} -> '{lote_nuevo.strip()}' | alma={row['co_alma'].strip()}")

print(f"\nTotal: {len(filas)} fila(s)")

if not filas:
    print("No hay duplicados. Sin accion necesaria.")
    conn.close()
    sys.exit(0)

if DRY_RUN:
    print("\n[DRY RUN] No se realizan cambios.")
    print("Para ejecutar: cambiar DRY_RUN = False")
    conn.close()
    sys.exit(0)

# EJECUTAR: Actualizar numero_lote de los duplicados AJUS
print("\n[EJECUTANDO] Actualizando numero_lote de filas AJUS duplicadas...")
try:
    updated = 0
    for f in filas:
        row     = dict(zip(cols, f))
        rg      = row['rowguid']
        lote_nuevo = (row['numero_lote'].strip() + '-ORI').ljust(20)[:20]
        
        cur.execute("""
        UPDATE saLoteEntrada
        SET numero_lote = ?
        WHERE rowguid = ?
          AND co_art = ?
          AND tipo_doc = 'AJUS'
          AND stock_actual = 0
        """, lote_nuevo, rg, ARTICULO)
        updated += cur.rowcount
        print(f"  Updated {cur.rowcount} row: {row['numero_lote'].strip()} -> {lote_nuevo.strip()}")

    print(f"\n  Total filas actualizadas: {updated}")
    
    # Verificar que ya no hay duplicados con el numero_lote original
    cur.execute(sql_dup)
    post = cur.fetchall()
    if post:
        print(f"  [ADVERTENCIA] Aun hay {len(post)} duplicados. ROLLBACK.")
        conn.rollback()
        sys.exit(1)
    
    conn.commit()
    print("  [OK] COMMIT exitoso.")
    print("  Los lotes AJUS duplicados fueron renombrados con sufijo '-ORI'.")
    print("  Ahora puedes reintentar el cierre 8855 de la orden 8844.")

except Exception as e:
    print(f"  [ERROR] {e}")
    conn.rollback()
    print("  ROLLBACK. Sin cambios.")
    sys.exit(1)
finally:
    conn.close()
