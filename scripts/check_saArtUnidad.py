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

print("Checking saArtUnidad for duplicated CAJ records")
with engine.connect() as conn:
    sql = text("""
        SELECT co_art, co_uni, equivalencia
        FROM saArtUnidad 
        WHERE co_art IN ('PT01P01X011', 'PT01D01X011') AND co_uni = 'CAJ'
    """)
    try:
        result = conn.execute(sql).fetchall()
        print("Rows returned:", len(result))
        for row in result:
            print(f"SKU: {row[0].strip()} | Unit: {row[1].strip()} | Equiv: {row[2]}")
            
        print("\nChecking all duplicate CAJ records in Profit Plus:")
        sql2 = text("""
            SELECT co_art, COUNT(*) as Count
            FROM saArtUnidad 
            WHERE co_uni = 'CAJ'
            GROUP BY co_art
            HAVING COUNT(*) > 1
        """)
        dupes = conn.execute(sql2).fetchall()
        print(f"Found {len(dupes)} SKUs with duplicated CAJ definitions:")
        for d in dupes:
            print(f"SKU: {d[0].strip()} has {d[1]} CAJ records")
    except Exception as e:
        print("Error:", e)
