"""
Encontrar la estructura correcta de tablas de stock/lote en carmal_a
"""
import pyodbc

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=192.168.1.205;DATABASE=carmal_a;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;'
)
cursor = conn.cursor()

print("=== TABLAS RELACIONADAS CON STOCK/LOTE/KARDEX ===")
cursor.execute("""
    SELECT TABLE_NAME 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_TYPE = 'BASE TABLE'
      AND (
        TABLE_NAME LIKE '%lote%'
        OR TABLE_NAME LIKE '%stock%'
        OR TABLE_NAME LIKE '%kardex%'
        OR TABLE_NAME LIKE '%alma%'
        OR TABLE_NAME LIKE '%alm%'
      )
    ORDER BY TABLE_NAME
""")
for row in cursor.fetchall():
    print(f"  {row[0]}")

print()
print("=== PRIMERAS 50 TABLAS DE saXXX ===")
cursor.execute("""
    SELECT TABLE_NAME 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_TYPE = 'BASE TABLE'
      AND TABLE_NAME LIKE 'sa%'
    ORDER BY TABLE_NAME
""")
for row in cursor.fetchall():
    print(f"  {row[0]}")

conn.close()
