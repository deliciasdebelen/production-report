import pyodbc
import sys

print("Iniciando prueba de conexión ODBC...")
try:
    conn_str = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=192.168.1.205;"
        "DATABASE=carmal_a;"
        "UID=PROFIT;"
        "PWD=profit;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "LoginTimeout=10;"
    )
    print(f"Connection String: {conn_str}")
    print("Intentando conectar a 192.168.1.205...")
    
    conn = pyodbc.connect(conn_str)
    print("¡CONEXIÓN EXITOSA!")
    
    cursor = conn.cursor()
    cursor.execute("SELECT @@VERSION")
    row = cursor.fetchone()
    print(f"Versión SQL Server Detectada: {row[0]}")
    
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f"\nFATAL ERROR: {e}")
    sys.exit(1)
