import pyodbc
import pandas as pd
from sqlalchemy import create_engine, text, inspect
import urllib

conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.1.205;"
    "DATABASE=carmal_a;"
    "UID=PROFIT;"
    "PWD=profit;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

def find_tables():
    params = urllib.parse.quote_plus(conn_str)
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
    
    # Find tables that contain 'lote' or 'mov' or 'inv' in the name
    df = pd.read_sql("""
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE'
          AND (TABLE_NAME LIKE '%lote%' 
            OR TABLE_NAME LIKE '%Lote%'
            OR TABLE_NAME LIKE '%mov%'
            OR TABLE_NAME LIKE '%Mov%'
            OR TABLE_NAME LIKE '%inv%'
            OR TABLE_NAME LIKE '%Inv%'
            OR TABLE_NAME LIKE '%aju%'
            OR TABLE_NAME LIKE '%Aju%')
        ORDER BY TABLE_NAME
    """, engine)
    print("Relevant tables in carmal_a:")
    print(df.to_string(index=False))

if __name__ == "__main__":
    find_tables()
