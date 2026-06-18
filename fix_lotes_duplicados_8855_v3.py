"""
fix_lotes_duplicados_8855_v3.py
================================
Fix del duplicado restante: MA250523-02 en P1-PP tiene 2 filas TRAS (n=2, stock=0).
Como ambas son tipo TRAS y stock=0, podemos eliminar la más antigua (la de menor cantidad)
ya que no tiene stock real.

También verifica si hay otros duplicados ocultos que causan el error en pCostoActualizarSalida.
"""
import pyodbc, sys

SERVER   = "192.168.1.205"
DATABASE = "CARMAL_A"
ARTICULO = "ST01D22X001"
DRY_RUN  = True   # Cambiar a False para ejecutar

def get_conn():
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SERVER};DATABASE={DATABASE};"
        f"UID=PROFIT;PWD=profit;"
        "Encrypt=yes;TrustServerCertificate=yes;",
        autocommit=False
    )

print(f"{'='*65}")
print(f"  FIX v3: Duplicados restantes en saLoteEntrada")
print(f"  Servidor: {SERVER} | Articulo: {ARTICULO}")
print(f"  MODO: {'DRY RUN' if DRY_RUN else '>>> EJECUCION REAL <<<'}")
print(f"{'='*65}")

conn = get_conn()
cur  = conn.cursor()

# 1. Ver estado actual - TODOS los duplicados de este articulo
print("\n=== Estado actual de duplicados ===")
cur.execute(f"""
SELECT numero_lote, co_alma, COUNT(*) AS n,
       SUM(stock_actual) AS stock_sum
FROM saLoteEntrada
WHERE co_art = '{ARTICULO}'
GROUP BY numero_lote, co_alma
HAVING COUNT(*) > 1
ORDER BY numero_lote, co_alma
""")
dups = cur.fetchall()
print(f"  Grupos con duplicados: {len(dups)}")
for d in dups:
    print(f"\n  lote={d[0].strip()} | alma={d[1].strip()} | n={d[2]} | stock_sum={d[3]}")

if not dups:
    print("  No hay duplicados. El error viene de otro lado.")
    conn.close()
    sys.exit(0)

# 2. Para MA250523-02 en P1-PP: ambas son TRAS con stock=0
# Verificar si tienen FK en saLoteSalida
print("\n=== Verificando FK en saLoteSalida para el duplicado P1-PP ===")
cur.execute(f"""
SELECT le.rowguid, le.numero_lote, le.co_alma, le.tipo_doc,
       le.cantidad, le.stock_actual,
       (SELECT COUNT(*) FROM saLoteSalida ls WHERE ls.Rowguid_Lote = le.rowguid) AS tiene_fk
FROM saLoteEntrada le
WHERE le.co_art = '{ARTICULO}'
  AND le.numero_lote = 'MA250523-02         '
  AND le.co_alma = 'P1-PP '
ORDER BY le.fe_us_in
""")
rows = cur.fetchall()
cols = [d[0] for d in cur.description]
print(f"  Filas para MA250523-02 / P1-PP:")
for r in rows:
    row = dict(zip(cols, r))
    print(f"    {row}")

# La fila con tiene_fk=0 y stock=0 es la candidata a eliminar o renombrar
candidates = [dict(zip(cols, r)) for r in rows if dict(zip(cols, r))['tiene_fk'] == 0 and dict(zip(cols, r))['stock_actual'] == 0]
print(f"\n  Candidatas a corregir (sin FK y sin stock): {len(candidates)}")
for c in candidates:
    print(f"    rowguid={c['rowguid']} tipo={c['tipo_doc']} cant={c['cantidad']}")

if DRY_RUN:
    print(f"\n  [DRY RUN] Sin cambios.")
    conn.close()
    sys.exit(0)

# EJECUTAR: Renombrar el candidato con sufijo -ORI para diferenciarlo
print("\n[EJECUTANDO] Renombrando lotes P1-PP duplicados con sufijo -ORI...")
try:
    updated = 0
    for c in candidates:
        rg = c['rowguid']
        lote_nuevo = ('MA250523-02-ORI').ljust(20)[:20]
        cur.execute("""
        UPDATE saLoteEntrada
        SET numero_lote = ?
        WHERE rowguid = ? AND co_art = ?
        """, lote_nuevo, rg, ARTICULO)
        updated += cur.rowcount
        print(f"  Updated {cur.rowcount}: rowguid={rg} -> {lote_nuevo.strip()}")

    # Verificar resultado
    cur.execute(f"""
    SELECT COUNT(*) FROM saLoteEntrada
    WHERE co_art = '{ARTICULO}'
      AND numero_lote = 'MA250523-02         '
      AND co_alma = 'P1-PP '
    """)
    remaining = cur.fetchone()[0]
    print(f"  Filas restantes con MA250523-02/P1-PP: {remaining}")

    conn.commit()
    print(f"  [OK] COMMIT. Total actualizadas: {updated}")

except Exception as e:
    print(f"  ERROR: {e}")
    conn.rollback()
    sys.exit(1)
finally:
    conn.close()

print("\nAhora verifica si el error es en pCostoActualizarSalida con el SP de SPCOSTOUNI_PT.")
print("Ejecuta el cierre nuevamente en Profit Plus.")
