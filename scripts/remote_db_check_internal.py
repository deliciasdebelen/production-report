import sqlalchemy
from sqlalchemy import text
import urllib.parse
import os

RAW_CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.1.205;"
    "DATABASE=carmal_a;"
    "UID=PROFIT;"
    "PWD=profit;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)
params_a = urllib.parse.quote_plus(RAW_CONN_STR)
EXTERNAL_DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={params_a}"
engine = sqlalchemy.create_engine(EXTERNAL_DATABASE_URL)

with engine.connect() as conn:
    print("Checking last 10 invoices:")
    # We also check for '00004' specifically
    res = conn.execute(text("SELECT TOP 10 doc_num, co_cli, campo5 FROM saFacturaVenta ORDER BY doc_num DESC")).fetchall()
    for r in res:
        print(f"NUM: {r.doc_num.strip()} | CLI: {r.co_cli.strip()} | C5: [{r.campo5.strip() if r.campo5 else 'NULL'}]")
    
    print("\nSearching specifically for 00004:")
    res4 = conn.execute(text("SELECT doc_num, co_cli, campo5 FROM saFacturaVenta WHERE doc_num LIKE '%00004%'")).fetchall()
    for r in res4:
        print(f"MATCH: {r.doc_num.strip()} | CLI: {r.co_cli.strip()} | C5: [{r.campo5.strip() if r.campo5 else 'NULL'}]")
