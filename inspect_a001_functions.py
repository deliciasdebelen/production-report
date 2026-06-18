import pyodbc

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=192.168.1.205;'
    'DATABASE=CARMAL_N;'
    'UID=profit;'
    'PWD=profit;'
    'Encrypt=no;'
    'TrustServerCertificate=yes'
)
cursor = conn.cursor()

print('=== GetValorCampo ===')
cursor.execute("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.GetValorCampo'))")
row = cursor.fetchone()
print(row[0] if row else 'NULL')

print()
print('=== GetCampo ===')
cursor.execute("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.GetCampo'))")
row = cursor.fetchone()
print(row[0] if row else 'NULL')

print()
print('=== All functions with ValorCampo in name ===')
cursor.execute("SELECT name FROM sys.objects WHERE type='FN' AND name LIKE '%ValorCampo%'")
for r in cursor.fetchall():
    print(r[0])

print()
print('=== GetCampoFecha or similar date-aware functions ===')
cursor.execute("SELECT name, OBJECT_DEFINITION(object_id) as def FROM sys.objects WHERE type='FN' AND (name LIKE '%Campoadi%' OR name LIKE '%GetCampo%' OR name LIKE '%ValorCampo%')")
for r in cursor.fetchall():
    print(f"--- {r[0]} ---")
    print(r[1])
    print()

print()
print('=== sncampadi table sample ===')
cursor.execute("SELECT TOP 3 * FROM sncampadi WHERE co_campadi LIKE 'A001%'")
cols = [d[0] for d in cursor.description]
print(cols)
for r in cursor.fetchall():
    print(list(r))

print()
print('=== snem_va table - A001 sample ===')
cursor.execute("SELECT TOP 5 * FROM snem_va WHERE co_var LIKE 'A001%'")
cols = [d[0] for d in cursor.description]
print(cols)
for r in cursor.fetchall():
    print(list(r))

print()
print('=== Tables with hist or em_va or campo ===')
cursor.execute("SELECT name FROM sys.tables WHERE name LIKE '%em_va%' OR name LIKE '%hist%' OR name LIKE '%campadi%' ORDER BY name")
for r in cursor.fetchall():
    print(r[0])

conn.close()
print("DONE")
