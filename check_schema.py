import pyodbc 
cs='DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.60.15;DATABASE=carmal_a;UID=PROFIT;PWD=profit;Encrypt=no;TrustServerCertificate=yes'
conn=pyodbc.connect(cs)
cursor=conn.cursor()

cursor.execute("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='saArtCompuestoGen'")
print("saArtCompuestoGen:")
for r in cursor.fetchall(): print(f"{r[0]} ({r[1]})")

print("---")
cursor.execute("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='saArtCompuestoGenReng'")
print("saArtCompuestoGenReng:")
for r in cursor.fetchall(): print(f"{r[0]} ({r[1]})")
