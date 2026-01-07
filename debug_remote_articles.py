import pyodbc
from sqlalchemy import create_engine, text
import os

# Production DB Config (from environment or hardcoded for test)
# USER provided: PROFIT / profit / 192.168.1.205 / carmal_a

SERVER = '192.168.1.205'
DATABASE = 'carmal_a'
USERNAME = 'PROFIT'
PASSWORD = 'profit'
DRIVER = 'ODBC Driver 17 for SQL Server'

# Connection String
DATABASE_URL = f"mssql+pyodbc://{USERNAME}:{PASSWORD}@{SERVER}/{DATABASE}?driver={DRIVER.replace(' ', '+')}&trust_server_certificate=yes"

def test_articles():
    print(f"Connecting to {SERVER}...")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            print("Connected. Executing query...")
            sql = text("""
                SELECT TOP 10
                    a.co_art as code,
                    a.art_des as description,
                    ISNULL((SELECT TOP 1 equivalencia 
                     FROM saartunidad 
                     WHERE co_art = a.co_art AND co_uni = 'CAJ'), 0) as box_equiv
                FROM saarticulo a
                WHERE a.anulado = 0 AND a.co_art LIKE 'PT%'
                ORDER BY a.art_des
            """)
            result = conn.execute(sql).fetchall()
            
            print(f"Found {len(result)} articles.")
            for row in result:
                print(f"Code: {row.code} | Desc: {row.description[:30]} | BoxEquiv: {row.box_equiv}")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_articles()
