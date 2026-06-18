"""
diag_schema_check.py
=====================
Verifica el esquema real de las tablas saAjusteReng y saStockAlmacen
para corregir los nombres de columna en el diagnóstico.
"""
import urllib
import pandas as pd
from sqlalchemy import create_engine

SERVER   = "192.168.60.15"
DATABASE = "CARMAL_A"
conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER};DATABASE={DATABASE};"
    f"UID=PROFIT;PWD=profit;"
    f"Encrypt=yes;TrustServerCertificate=yes;"
)
params = urllib.parse.quote_plus(conn_str)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

for tabla in ["saAjusteReng", "saStockAlmacen", "saLoteEntrada", "saLoteSalida"]:
    print(f"\n{'='*50}")
    print(f"  Columnas de: {tabla}")
    print("="*50)
    try:
        df = pd.read_sql(f"""
            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{tabla}'
            ORDER BY ORDINAL_POSITION
        """, engine)
        print(df.to_string(index=False))
    except Exception as e:
        print(f"  ❌ Error: {e}")
