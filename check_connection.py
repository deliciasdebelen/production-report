import pymssql
import sys

# Connection details
server = '192.168.1.205'
port = 1433
user = 'PROFIT'
password = 'profit' # Inferred from context or needs check
database = 'carmal_a'

try:
    print(f"Attempting to connect to {server}:{port} as {user}...")
    conn = pymssql.connect(
        server=server,
        user=user,
        password=password,
        database=database,
        port=port,
        charset='utf8',
        login_timeout=5
    )
    print("SUCCESS: Connected to SQL Server!")
    
    cursor = conn.cursor()
    cursor.execute("SELECT TOP 1 art_des FROM saarticulo")
    row = cursor.fetchone()
    print(f"Query Test Result: {row}")
    
    conn.close()
except Exception as e:
    print(f"FAILURE: Could not connect. Error: {e}")
