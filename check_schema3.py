import pyodbc 
cs='DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.60.15;DATABASE=carmal_a;UID=PROFIT;PWD=profit;Encrypt=no;TrustServerCertificate=yes'
conn=pyodbc.connect(cs)
cursor=conn.cursor()

cursor.execute("SELECT TOP 5 co_artc, descrip, co_art, co_uni FROM saArtCompuesto")
print("saArtCompuesto (BOM Header):")
for r in cursor.fetchall(): print(r)

print("---")
cursor.execute("SELECT TOP 5 co_artc, co_art, co_uni, total_art FROM saArtCompuestoReng")
print("saArtCompuestoReng (BOM Lines):")
for r in cursor.fetchall(): print(r)
