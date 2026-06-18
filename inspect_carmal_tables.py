"""
Analizar inconsistencias de stock en carmal_a.
Tablas: saLoteEntrada, saStockAlmacen, saAjuste, saAjusteReng
"""
import pyodbc

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=192.168.1.205;DATABASE=carmal_a;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;'
)
cursor = conn.cursor()

# Primero, entender estructura de saLoteEntrada
print("=== Columnas de saLoteEntrada ===")
cursor.execute("""
    SELECT COLUMN_NAME, DATA_TYPE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'saLoteEntrada'
    ORDER BY ORDINAL_POSITION
""")
cols = cursor.fetchall()
for c in cols:
    print(f"  {c[0]} ({c[1]})")

print()
print("=== Columnas de saStockAlmacen ===")
cursor.execute("""
    SELECT COLUMN_NAME, DATA_TYPE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'saStockAlmacen'
    ORDER BY ORDINAL_POSITION
""")
cols = cursor.fetchall()
for c in cols:
    print(f"  {c[0]} ({c[1]})")

print()
print("=== Columnas de saAjuste / saAjusteReng ===")
cursor.execute("""
    SELECT COLUMN_NAME, DATA_TYPE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'saAjuste'
    ORDER BY ORDINAL_POSITION
""")
for c in cursor.fetchall():
    print(f"  saAjuste.{c[0]} ({c[1]})")

cursor.execute("""
    SELECT COLUMN_NAME, DATA_TYPE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'saAjusteReng'
    ORDER BY ORDINAL_POSITION
""")
for c in cursor.fetchall():
    print(f"  saAjusteReng.{c[0]} ({c[1]})")

# Muestra de datos de saLoteEntrada para uno de los lotes
print()
print("=== Muestra de saLoteEntrada para L1260226-01 ===")
cursor.execute("""
    SELECT TOP 5 * FROM saLoteEntrada WHERE co_lote = 'L1260226-01'
""")
rows = cursor.fetchall()
if rows:
    desc = [d[0] for d in cursor.description]
    print(f"  Cols: {desc}")
    for r in rows:
        print(f"  {list(r)}")
else:
    print("  Sin resultados")

conn.close()
