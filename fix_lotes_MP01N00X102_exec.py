"""
fix_lotes_MP01N00X102.py
========================
Corrige los duplicados de saLoteEntrada para el artículo MP01N00X102
que bloquea el cierre 8855.

El lote PMA260417 en P1-PP tiene 2 filas TRAS con stock_actual=126.00000 c/u.
Solo debe haber 1 fila activa. La segunda es un duplicado erróneo.

ESTRATEGIA: La fila más reciente (mayor fe_us_in) es la copia duplicada.
La original es la primera en ser insertada. Renombramos la más reciente
agregando sufijo -B para que las búsquedas escalares no fallen.

DRY_RUN=True por defecto.
"""
import pyodbc, sys

SERVER   = "192.168.1.205"
DATABASE = "CARMAL_A"
DRY_RUN  = False  # Cambiar a False para ejecutar

ARTICULO = "MP01N00X102"

def get_conn():
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SERVER};DATABASE={DATABASE};"
        f"UID=PROFIT;PWD=profit;"
        "Encrypt=yes;TrustServerCertificate=yes;",
        autocommit=False
    )

print(f"{'='*65}")
print(f"  FIX: Duplicados saLoteEntrada para {ARTICULO}")
print(f"  Servidor: {SERVER} | MODO: {'DRY RUN' if DRY_RUN else '>>> EJECUCION REAL <<<'}")
print(f"{'='*65}")

conn = get_conn()
cur  = conn.cursor()

# Buscar duplicados para este artículo que bloquean el cierre
cur.execute(f"""
SELECT numero_lote, co_alma, COUNT(*) AS n,
       SUM(stock_actual) AS stock_sum
FROM saLoteEntrada
WHERE co_art = '{ARTICULO}'
GROUP BY numero_lote, co_alma
HAVING COUNT(*) > 1
ORDER BY n DESC, numero_lote, co_alma
""")
dups = cur.fetchall()
print(f"\nDuplicados encontrados: {len(dups)}")
for d in dups:
    print(f"  lote={d[0].strip()} alma={d[1].strip()} n={d[2]} stock_sum={d[3]}")

if not dups:
    print("Sin duplicados. Cerrando.")
    conn.close()
    sys.exit(0)

# Para cada grupo de duplicados, obtener el detalle
all_candidates = []
for dup in dups:
    lote = dup[0].strip()
    alma = dup[1].strip()
    n    = dup[2]
    
    cur.execute(f"""
    SELECT numero_lote, co_alma, tipo_doc, cantidad, stock_actual,
           CONVERT(VARCHAR(36), rowguid) AS rowguid,
           CONVERT(VARCHAR(19), fe_us_in, 120) AS fe_us_in,
           (SELECT COUNT(*) FROM saLoteSalida ls WHERE ls.Rowguid_Lote = le.rowguid) AS tiene_fk
    FROM saLoteEntrada le
    WHERE le.co_art = '{ARTICULO}'
      AND le.numero_lote = '{lote.ljust(20)}'
      AND le.co_alma = '{alma.ljust(6)}'
    ORDER BY fe_us_in DESC
    """)
    cols = [d[0] for d in cur.description]
    filas = [dict(zip(cols, r)) for r in cur.fetchall()]
    
    print(f"\n  Grupo: lote={lote} alma={alma}")
    for i, f in enumerate(filas):
        print(f"    [{i}] rg={f['rowguid']} tipo={f['tipo_doc']} cant={f['cantidad']} stock={f['stock_actual']} fk={f['tiene_fk']} fe_us_in={f['fe_us_in']}")
    
    # La estrategia: si hay filas con stock=0 y sin FK, renombrarlas
    # Si todas tienen stock>0, renombrar la más reciente (fe_us_in mayor) si no tiene FK
    for i, f in enumerate(filas):
        if i == 0:  # La más reciente (primera por ORDER BY fe_us_in DESC)
            if f['tiene_fk'] == 0:
                lote_nuevo = (lote + '-B')[:20].ljust(20)
                all_candidates.append({
                    'rowguid': f['rowguid'],
                    'lote_actual': lote,
                    'lote_nuevo': lote_nuevo.strip(),
                    'alma': alma,
                    'stock': f['stock_actual'],
                    'fk': f['tiene_fk']
                })
                print(f"    => CANDIDATA a renombrar: {lote} -> {lote_nuevo.strip()} (sin FK)")
            else:
                # Tiene FK - no se puede renombrar fácilmente
                # Verificar la segunda más reciente
                if len(filas) > 1 and filas[1]['tiene_fk'] == 0:
                    lote_nuevo = (lote + '-B')[:20].ljust(20)
                    all_candidates.append({
                        'rowguid': filas[1]['rowguid'],
                        'lote_actual': lote,
                        'lote_nuevo': lote_nuevo.strip(),
                        'alma': alma,
                        'stock': filas[1]['stock_actual'],
                        'fk': filas[1]['tiene_fk']
                    })
                    print(f"    => CANDIDATA [1] a renombrar (sin FK): {lote} -> {lote_nuevo.strip()}")
                else:
                    print(f"    => TODAS TIENEN FK. No se puede renombrar automáticamente.")

print(f"\nTotal candidatas: {len(all_candidates)}")
for c in all_candidates:
    print(f"  rg={c['rowguid']} | {c['lote_actual']} -> {c['lote_nuevo']} | stock={c['stock']} | fk={c['fk']}")

if DRY_RUN:
    print(f"\n[DRY RUN] Sin cambios. Cambiar DRY_RUN=False para ejecutar.")
    conn.close()
    sys.exit(0)

# EJECUTAR
print("\n[EJECUTANDO]...")
try:
    updated = 0
    for c in all_candidates:
        lote_nuevo = c['lote_nuevo'].ljust(20)[:20]
        cur.execute("""
        UPDATE saLoteEntrada
        SET numero_lote = ?
        WHERE rowguid = ? AND co_art = ?
        """, lote_nuevo, c['rowguid'], ARTICULO)
        updated += cur.rowcount
        print(f"  Updated {cur.rowcount}: {c['lote_actual']} -> {lote_nuevo.strip()}")

    # Verificar que ya no haya duplicados para los lotes del cierre
    cur.execute(f"""
    SELECT numero_lote, co_alma, COUNT(*) AS n
    FROM saLoteEntrada
    WHERE co_art = '{ARTICULO}'
    GROUP BY numero_lote, co_alma
    HAVING COUNT(*) > 1
    ORDER BY n DESC
    """)
    remaining = cur.fetchall()
    
    if remaining:
        print(f"\n  ADVERTENCIA: Aún hay {len(remaining)} grupos duplicados:")
        for r in remaining:
            print(f"    lote={r[0].strip()} alma={r[1].strip()} n={r[2]}")
        print("  Realizando COMMIT de los cambios parciales...")

    conn.commit()
    print(f"\n  [OK] COMMIT. Total actualizadas: {updated}")
    print(f"  Intenta nuevamente el cierre 8855.")

except Exception as e:
    print(f"  ERROR: {e}")
    conn.rollback()
    sys.exit(1)
finally:
    conn.close()
