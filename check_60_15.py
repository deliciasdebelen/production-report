import urllib, pandas as pd
from sqlalchemy import create_engine, text

# Try connecting with same credentials
SERVER = "192.168.60.15"
conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};UID=PROFIT;PWD=profit;Encrypt=yes;TrustServerCertificate=yes;"
params = urllib.parse.quote_plus(conn_str)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

try:
    # List all databases
    df_dbs = pd.read_sql("SELECT name FROM sys.databases ORDER BY name", engine)
    print("Databases on 192.168.60.15:")
    print(df_dbs.to_string(index=False))
except Exception as e:
    print(f"Connection error: {e}")
