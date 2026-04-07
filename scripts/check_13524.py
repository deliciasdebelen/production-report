import json
from sqlalchemy import create_engine, text

PROFIT_URL = (
    "mssql+pyodbc:///?odbc_connect="
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.1.205;"
    "DATABASE=carmal_a;"
    "UID=PROFIT;"
    "PWD=profit;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)
engine = create_engine(PROFIT_URL)

with engine.connect() as conn:
    sql = text("""
        SELECT R.reng_num, R.co_art, LTRIM(RTRIM(A.art_des)) as art_des, R.total_art 
        FROM saFacturaVentaReng R
        JOIN saArticulo A ON R.co_art = A.co_art
        WHERE R.doc_num LIKE '%13524'
    """)
    result = conn.execute(sql).fetchall()
    print("Checking doc 13524:")
    for row in result:
        print(f"SKU: {row[1].strip()} | Desc: {row[2]} | Qty: {row[3]}")
