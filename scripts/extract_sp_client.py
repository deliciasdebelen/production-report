import pyodbc

conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.1.205;"
    "DATABASE=carmal_a;"
    "UID=PROFIT;"
    "PWD=profit;"
)
try:
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT definition 
            FROM sys.sql_modules m 
            JOIN sys.objects o ON m.object_id = o.object_id 
            WHERE o.name = 'SP_CRM_FacturasPendientesPorCliente'
        """)
        row = cursor.fetchone()
        if row:
            print("--- SP_CRM_FacturasPendientesPorCliente ---")
            print(row[0])
        else:
            print("Procedure not found.")
except Exception as e:
    print(f"Error: {e}")
