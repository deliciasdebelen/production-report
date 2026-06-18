import urllib, pandas as pd
from sqlalchemy import create_engine

conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;DATABASE=carmal_a;UID=PROFIT;PWD=profit;Encrypt=yes;TrustServerCertificate=yes;"
params = urllib.parse.quote_plus(conn_str)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

# 1. Find nota credito table name
df_nota_tables = pd.read_sql("""
    SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_NAME LIKE '%nota%' OR TABLE_NAME LIKE '%Nota%'
       OR TABLE_NAME LIKE '%NCr%' OR TABLE_NAME LIKE '%NCV%'
    ORDER BY TABLE_NAME
""", engine)
print("Tablas tipo Nota:", df_nota_tables.to_string(index=False))

# 2. Triggers
df_trg = pd.read_sql("""
    SELECT t.name AS trigger_name, o.name AS table_name, t.is_disabled
    FROM sys.triggers t
    JOIN sys.objects o ON t.parent_id = o.object_id
    WHERE o.name IN ('saCobro','saCobroDocReng','saCobroTPReng')
""", engine)
print("\n=== TRIGGERS sobre tablas de cobro ===")
print(df_trg.to_string(index=False) if len(df_trg) else "Ningun trigger en tablas de cobro.")

# 3. SPs
df_sp = pd.read_sql("""
    SELECT r.ROUTINE_NAME, r.ROUTINE_TYPE
    FROM INFORMATION_SCHEMA.ROUTINES r
    WHERE r.ROUTINE_DEFINITION LIKE '%saCobro%'
    ORDER BY r.ROUTINE_NAME
""", engine)
print("\n=== SPs que referencian saCobro ===")
print(df_sp.to_string(index=False) if len(df_sp) else "Ninguno encontrado.")

# 4. Check if there is any VIEW or similar related to cobros
df_views = pd.read_sql("""
    SELECT TABLE_NAME FROM INFORMATION_SCHEMA.VIEWS
    WHERE TABLE_NAME LIKE '%cobro%' OR TABLE_NAME LIKE '%pago%'
    ORDER BY TABLE_NAME
""", engine)
print("\n=== VISTAS relacionadas con cobros ===")
print(df_views.to_string(index=False) if len(df_views) else "Ninguna vista encontrada.")
