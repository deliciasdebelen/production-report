import pyodbc

ca_prod = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;'
    'DATABASE=CARMAL_A;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;',
    autocommit=True
)
cur = ca_prod.cursor()

# pActualizarLote is called when a lote movement is made
# It likely does: UPDATE saLoteEntrada SET stock_actual = stock_actual - @cantidad
# WHERE co_art = @art AND numero_lote = @lote AND co_alma = @alma
# If there are 2 rows matching, this UPDATE affects 2 rows (not a 1453 error)
# BUT if it's using a scalar subquery like:
# SET stock_actual = (SELECT stock_actual FROM saLoteEntrada WHERE ...) - @cantidad
# Then it would fail with 1453

print("=== pActualizarLote ===")
cur.execute("EXEC sp_helptext 'pActualizarLote'")
rows = cur.fetchall()
text = "".join(r[0] for r in rows)
print(f"Length: {len(text)}")
print(text[:5000])

print("\n\n=== pValidarLoteEntradaNoOrigen1 (modified 2025-05-30) ===")
cur.execute("EXEC sp_helptext 'pValidarLoteEntradaNoOrigen1'")
rows2 = cur.fetchall()
text2 = "".join(r[0] for r in rows2)
print(f"Length: {len(text2)}")
print(text2[:5000])

print("\n\n=== nsa_ASIGNACIONDELOTES_Sal (modified 2026-01-08) ===")
cur.execute("EXEC sp_helptext 'nsa_ASIGNACIONDELOTES_Sal'")
rows3 = cur.fetchall()
text3 = "".join(r[0] for r in rows3)
print(f"Length: {len(text3)}")
# Find the critical subconsulta escalar
lines3 = text3.split('\n')
for i, line in enumerate(lines3):
    ls = line.strip()
    if 'saLoteEntrada' in ls:
        start = max(0, i-3)
        end = min(len(lines3), i+5)
        print(f"\n  Contexto linea {i}:")
        for j in range(start, end):
            print(f"    {'>>>' if j==i else '   '} {lines3[j].rstrip()}")
print("\nFull text:")
print(text3[:8000])

ca_prod.close()
print("\nDone.")
