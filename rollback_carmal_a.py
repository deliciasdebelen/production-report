"""
rollback_carmal_a.py
====================
Revierte EXACTAMENTE los cambios de hoy en CARMAL_A.dbo.saLoteEntrada.
Usa los rowguids exactos de cada fila modificada.

CAMBIO 1 — fix_lotes_duplicados_8855_v2_exec.py (ST01D22X001):
  4 filas AJUS renombradas con sufijo -ORI en P1-ST

CAMBIO 2 — fix_lotes_MP01N00X102_exec.py (MP01N00X102):
  5 filas renombradas con sufijo -B
"""
import pyodbc

SERVER   = "192.168.1.205"
DATABASE = "CARMAL_A"

# Mapa exacto: rowguid -> (numero_lote_actual, numero_lote_original, co_art)
ROLLBACK_MAP = [
    # ── CAMBIO 1: ST01D22X001 ─────────────────────────────────────────────
    ("42DB1CB5-99D2-4594-A859-25D99E02B588", "MA250523-01-ORI     ", "MA250523-01         ", "ST01D22X001"),
    ("82354C05-13DE-4E69-ACF5-DC876217A0C8", "MA250523-02-ORI     ", "MA250523-02         ", "ST01D22X001"),
    ("BE029548-B72C-4E0A-9F51-93F0DCA002D1", "MA250526-01-ORI     ", "MA250526-01         ", "ST01D22X001"),
    ("6B89132D-EF14-4836-B89E-9700606C580B", "MA250526-02-ORI     ", "MA250526-02         ", "ST01D22X001"),
    # ── CAMBIO 2: MP01N00X102 ─────────────────────────────────────────────
    ("22A47CEC-7306-4F18-A4B2-D8F6BDB24FAF", "PMA240304-B         ", "PMA240304           ", "MP01N00X102"),
    ("C49F82F3-4701-4100-9AC8-C75779A98AAE", "PMA240502-B         ", "PMA240502           ", "MP01N00X102"),
    ("C6E9C62F-BB94-41C5-BB7D-235F08F2F3C3", "PMA240503-B         ", "PMA240503           ", "MP01N00X102"),
    ("7ACF8835-FF51-41E8-9D1C-32A744493C7D", "PMA240506-B         ", "PMA240506           ", "MP01N00X102"),
    ("6DD0CE4A-13B7-4F8D-B9D6-FE06D43EB9EF", "PMA260417-B         ", "PMA260417           ", "MP01N00X102"),
]

conn = pyodbc.connect(
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER};DATABASE={DATABASE};"
    f"UID=PROFIT;PWD=profit;"
    "Encrypt=yes;TrustServerCertificate=yes;",
    autocommit=False
)
cur = conn.cursor()

print("=" * 65)
print(f"  ROLLBACK CARMAL_A.dbo.saLoteEntrada")
print(f"  Servidor: {SERVER}")
print("=" * 65)

# ── Verificar estado actual antes de tocar nada ───────────────────────────
print("\n[1] Verificando estado actual de cada fila...")
filas_ok    = []
filas_warn  = []

for rg, lote_actual, lote_orig, art in ROLLBACK_MAP:
    cur.execute("""
    SELECT numero_lote, co_art, co_alma, tipo_doc, stock_actual
    FROM saLoteEntrada
    WHERE rowguid = ?
    """, rg)
    row = cur.fetchone()

    if row is None:
        filas_warn.append((rg, "NO ENCONTRADA"))
        print(f"  WARN  rg={rg[:8]}... -> FILA NO ENCONTRADA")
    elif row[0].strip() == lote_actual.strip():
        filas_ok.append((rg, lote_actual, lote_orig, art))
        print(f"  OK    rg={rg[:8]}... | {lote_actual.strip()} -> {lote_orig.strip()} ({art})")
    elif row[0].strip() == lote_orig.strip():
        filas_warn.append((rg, f"YA REVERTIDA (numero_lote={row[0].strip()})"))
        print(f"  SKIP  rg={rg[:8]}... -> YA tiene el valor original ({row[0].strip()})")
    else:
        filas_warn.append((rg, f"VALOR INESPERADO: {row[0].strip()}"))
        print(f"  WARN  rg={rg[:8]}... -> numero_lote actual='{row[0].strip()}' (inesperado)")

print(f"\n  Filas a revertir: {len(filas_ok)}")
print(f"  Advertencias:     {len(filas_warn)}")

if not filas_ok:
    print("\n  Nada que revertir. Saliendo.")
    conn.close()
    exit(0)

# ── Ejecutar rollback ─────────────────────────────────────────────────────
print("\n[2] Ejecutando rollback...")
try:
    total = 0
    for rg, lote_actual, lote_orig, art in filas_ok:
        cur.execute("""
        UPDATE saLoteEntrada
        SET numero_lote = ?
        WHERE rowguid = ?
          AND co_art   LIKE ?
          AND numero_lote = ?
        """, lote_orig, rg, art + "%", lote_actual)
        n = cur.rowcount
        total += n
        estado = "OK" if n == 1 else f"WARN (rows={n})"
        print(f"  {estado}  rg={rg[:8]}... | {lote_actual.strip()} -> {lote_orig.strip()}")

    if total == len(filas_ok):
        conn.commit()
        print(f"\n  [COMMIT] {total} fila(s) revertidas exitosamente.")
    else:
        conn.rollback()
        print(f"\n  [ROLLBACK] Mismatch: esperadas={len(filas_ok)}, actualizadas={total}. Sin cambios.")
        exit(1)

except Exception as e:
    conn.rollback()
    print(f"\n  [ERROR] {e}")
    print("  ROLLBACK aplicado. Sin cambios en la base de datos.")
    exit(1)
finally:
    conn.close()

# ── Verificacion final ────────────────────────────────────────────────────
print("\n[3] Verificacion final — duplicados para los articulos afectados:")
conn2 = pyodbc.connect(
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER};DATABASE={DATABASE};"
    f"UID=PROFIT;PWD=profit;"
    "Encrypt=yes;TrustServerCertificate=yes;",
    autocommit=True
)
cur2 = conn2.cursor()
for art in ["ST01D22X001", "MP01N00X102"]:
    cur2.execute(f"""
    SELECT numero_lote, co_alma, COUNT(*) AS n
    FROM saLoteEntrada
    WHERE co_art = '{art}'
    GROUP BY numero_lote, co_alma
    HAVING COUNT(*) > 1
    """)
    dups = cur2.fetchall()
    print(f"  {art}: {len(dups)} grupo(s) con duplicados" +
          (" (estado pre-fix restaurado)" if dups else " OK"))
conn2.close()
print("\nRollback completado.")
