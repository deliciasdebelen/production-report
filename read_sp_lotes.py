import urllib, pandas as pd
from sqlalchemy import create_engine

conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;DATABASE=carmal_a;UID=PROFIT;PWD=profit;Encrypt=yes;TrustServerCertificate=yes;"
params = urllib.parse.quote_plus(conn_str)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

# Get all SPs that contain saLoteEntrada AND selection logic
df_sp = pd.read_sql("""
    SELECT r.ROUTINE_NAME, r.ROUTINE_TYPE, r.ROUTINE_DEFINITION
    FROM INFORMATION_SCHEMA.ROUTINES r
    WHERE r.ROUTINE_DEFINITION LIKE '%saLoteEntrada%'
      AND (
           r.ROUTINE_DEFINITION LIKE '%stock_actual%'
        OR r.ROUTINE_DEFINITION LIKE '%numero_lote%'
      )
      AND r.ROUTINE_TYPE IN ('PROCEDURE', 'FUNCTION')
    ORDER BY r.ROUTINE_NAME
""", engine)

print(f"Total SPs/Functions that reference saLoteEntrada + stock_actual/numero_lote: {len(df_sp)}")
for _, row in df_sp.iterrows():
    print(f"\n{'='*70}")
    print(f"SP: {row['ROUTINE_NAME']} ({row['ROUTINE_TYPE']})")
    print(f"{'='*70}")
    print(row['ROUTINE_DEFINITION'])
    print()
