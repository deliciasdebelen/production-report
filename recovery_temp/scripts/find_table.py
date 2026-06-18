import urllib.parse
from sqlalchemy import create_engine, text

DEFAULT_SERVER = "192.168.1.205"
DB_NAME = "carmal_m"

def get_engine():
    driver = "ODBC Driver 17 for SQL Server"
    base_conn = (
        f"DRIVER={{{driver}}};"
        f"SERVER={DEFAULT_SERVER};"
        f"DATABASE={DB_NAME};"
        "UID=PROFIT;"
        "PWD=profit;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )
    params = urllib.parse.quote_plus(base_conn)
    url = f"mssql+pyodbc:///?odbc_connect={params}"
    return create_engine(url)

def find():
    engine = get_engine()
    try:
        with engine.connect() as conn:
            print(f"Connected to {DB_NAME}. Searching...")
            
            # Search for Formula
            print("--- LIKE '%Formula%' ---")
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%Formula%'")).fetchall()
            if not result:
                print("No matches found.")
            for r in result:
                print(r[0])
                
            # Search for Composicion
            print("--- LIKE '%Composicion%' ---")
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%Composi%'")).fetchall()
            for r in result:
                print(r[0])

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find()
