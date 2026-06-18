import urllib, pandas as pd
from sqlalchemy import create_engine

conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;DATABASE=carmal_a;UID=PROFIT;PWD=profit;Encrypt=yes;TrustServerCertificate=yes;"
params = urllib.parse.quote_plus(conn_str)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

# Get names of all SPs that use saLoteEntrada in a SELECT without stock_actual > 0 filter
df_sp = pd.read_sql("""
    SELECT r.ROUTINE_NAME, r.ROUTINE_TYPE, r.ROUTINE_DEFINITION
    FROM INFORMATION_SCHEMA.ROUTINES r
    WHERE r.ROUTINE_DEFINITION LIKE '%saLoteEntrada%'
      AND r.ROUTINE_TYPE IN ('PROCEDURE', 'FUNCTION')
    ORDER BY r.ROUTINE_NAME
""", engine)

print(f"Total SPs con saLoteEntrada: {len(df_sp)}\n")

# Classify each SP by whether it has stock_actual filter
selection_sps = []
update_sps = []
report_sps = []
safe_sps = []

for _, row in df_sp.iterrows():
    defn = row['ROUTINE_DEFINITION'].upper()
    name = row['ROUTINE_NAME']
    
    has_stock_filter = 'STOCK_ACTUAL > 0' in defn or 'STOCK_ACTUAL>0' in defn
    has_update = 'UPDATE SALOTEENTRADA' in defn or 'SET STOCK_ACTUAL' in defn
    has_select = 'SELECT' in defn and 'SALOTEENTRADA' in defn
    has_insert = 'INSERT INTO SALOTEENTRADA' in defn
    is_report = name.upper().startswith('REP')
    
    if has_update:
        update_sps.append(name)
    elif is_report:
        report_sps.append(name)
    elif has_select and not has_stock_filter:
        selection_sps.append((name, row['ROUTINE_TYPE']))
    elif has_select and has_stock_filter:
        safe_sps.append(name)

print("=== SPs/Functions YA CON FILTRO stock_actual > 0 (CORRECTOS) ===")
for s in safe_sps:
    print(f"  ✅ {s}")

print("\n=== SPs/Functions que SELECCIONAN saLoteEntrada SIN FILTRO (RIESGO) ===")
for s, t in selection_sps:
    print(f"  ⚠️  {s} ({t})")

print("\n=== SPs que ACTUALIZAN stock_actual ===")
for s in update_sps:
    print(f"  🔧 {s}")

print("\n=== SPs de REPORTE (menor riesgo) ===")
for s in report_sps:
    print(f"  📋 {s}")
