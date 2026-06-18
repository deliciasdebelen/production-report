"""
fix_lle_pp.py - Limpieza de filas LLE en saStockAlmacen / P1-PP
Autorizado por el usuario el 2026-04-29.
"""
import pyodbc

ca = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;'
    'DATABASE=CARMAL_A;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;',
    autocommit=False  # transaccion manual
)
cur = ca.cursor()

ARTS = ['AC01N00A016', 'EC11N00X003', 'ME04N00X',
        'ME05N00X012', 'NP06N00X038', 'NP06N00X039']

SEP = "=" * 60

# ── PASO 1: Verificacion pre-ejecucion ────────────────────────
print(f"{SEP}\n  PASO 1 — VERIFICACION PRE-EJECUCION\n{SEP}")
cur.execute("""
SELECT co_art, tipo, CAST(stock AS VARCHAR(20)) AS stock
FROM saStockAlmacen
WHERE tipo = 'LLE ' AND co_alma = 'P1-PP '
ORDER BY co_art
""")
filas_lle = cur.fetchall()
print(f"  Filas LLE en P1-PP encontradas: {len(filas_lle)}")
for r in filas_lle:
    print(f"  art={r[0].strip()} tipo={r[1].strip()} stock={r[2]}")

if len(filas_lle) != 6:
    print(f"\n  ABORT: Se esperaban 6 filas, se encontraron {len(filas_lle)}.")
    print("  No se ejecuta el DELETE. Verificar manualmente.")
    ca.close()
    exit(1)

# Verificar que todas tienen stock = 0
non_zero = [(r[0], r[2]) for r in filas_lle if float(r[2]) != 0.0]
if non_zero:
    print(f"\n  ABORT: Hay filas con stock != 0: {non_zero}")
    print("  No se ejecuta. Requiere revision manual.")
    ca.close()
    exit(1)

# Verificar que existe fila ACT para cada art
print(f"\n  Verificando filas ACT (deben existir para cada art):")
for art in ARTS:
    cur.execute(f"""
    SELECT CAST(stock AS VARCHAR(20)) AS stock
    FROM saStockAlmacen
    WHERE co_art = '{art}' AND co_alma = 'P1-PP ' AND tipo = 'ACT '
    """)
    r = cur.fetchone()
    if not r:
        print(f"  ABORT: No existe fila ACT para {art}. Abortar.")
        ca.close()
        exit(1)
    print(f"  art={art} ACT stock={r[0]} ✓")

print("\n  Todas las verificaciones previas pasaron. Procediendo...")

# ── PASO 2: DELETE dentro de transaccion ──────────────────────
print(f"\n{SEP}\n  PASO 2 — DELETE (TRANSACCION)\n{SEP}")
try:
    cur.execute("""
    DELETE FROM saStockAlmacen
    WHERE tipo   = 'LLE '
      AND co_alma = 'P1-PP '
      AND stock   = 0
    """)
    filas_eliminadas = cur.rowcount
    print(f"  Filas eliminadas: {filas_eliminadas}")

    if filas_eliminadas != 6:
        print(f"  ROLLBACK: Se esperaban 6 filas eliminadas, se eliminaron {filas_eliminadas}.")
        ca.rollback()
        ca.close()
        exit(1)

    ca.commit()
    print("  COMMIT aplicado exitosamente.")

except Exception as e:
    ca.rollback()
    print(f"  ROLLBACK por excepcion: {e}")
    ca.close()
    exit(1)

# ── PASO 3: Verificacion post-ejecucion ───────────────────────
print(f"\n{SEP}\n  PASO 3 — VERIFICACION POST-EJECUCION\n{SEP}")

# 3a. No deben quedar filas LLE en P1-PP
ca2 = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;'
    'DATABASE=CARMAL_A;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;', autocommit=True)
cur2 = ca2.cursor()

cur2.execute("""
SELECT COUNT(*) FROM saStockAlmacen
WHERE tipo = 'LLE ' AND co_alma = 'P1-PP '
""")
restantes = cur2.fetchone()[0]
print(f"  Filas LLE restantes en P1-PP: {restantes}")
if restantes == 0:
    print("  OK — Ninguna fila LLE en P1-PP.")
else:
    print(f"  ADVERTENCIA: Quedan {restantes} filas LLE en P1-PP.")

# 3b. Filas ACT deben seguir intactas
print(f"\n  Verificando integridad filas ACT post-limpieza:")
cur2.execute(f"""
SELECT co_art, tipo, CAST(stock AS VARCHAR(20)) AS stock
FROM saStockAlmacen
WHERE co_alma = 'P1-PP '
  AND co_art IN ({','.join([f"'{a}'" for a in ARTS])})
ORDER BY co_art
""")
actos = cur2.fetchall()
print(f"  Filas ACT encontradas: {len(actos)} (esperadas: 6)")
for r in actos:
    print(f"  art={r[0].strip()} tipo={r[1].strip()} stock={r[2]} ✓")

# 3c. Verificar que saStockAlmacen P1-PP no tiene duplicados para estos arts
print(f"\n  Verificando que no hay duplicados (n_filas por art):")
all_clean = True
for art in ARTS:
    cur2.execute(f"""
    SELECT COUNT(*) FROM saStockAlmacen
    WHERE co_art = '{art}' AND co_alma = 'P1-PP '
    """)
    n = cur2.fetchone()[0]
    status = "OK — 1 fila" if n == 1 else f"*** {n} filas"
    print(f"  {art}: {n} fila(s) — {status}")
    if n != 1:
        all_clean = False

ca2.close()
ca.close()

print(f"\n{SEP}")
if restantes == 0 and all_clean:
    print("  RESULTADO: LIMPIEZA EXITOSA")
    print("  Los 6 articulos en P1-PP ya no tienen filas LLE duplicadas.")
    print("  El almacen P1-PP esta limpio para futuros cierres.")
else:
    print("  RESULTADO: VERIFICACION CON ADVERTENCIAS — revisar arriba.")
print(SEP)
