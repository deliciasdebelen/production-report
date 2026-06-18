import urllib.parse
from sqlalchemy import create_engine, text

params = urllib.parse.quote_plus(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.1.205;"
    "DATABASE=carmal_a;"
    "UID=PROFIT;"
    "PWD=profit;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

def debug_cols():
    target = "J411903523"
    print(f"--- Getting Columns for {target} ---")
    with engine.connect() as conn:
        # Use simple string interpolation to avoid any binding weirdness for this test
        sql = text(f"EXEC SP_CRM_FacturasPendientesPorCliente @co_cli = '{target}'")
        result = conn.execute(sql)
        print("Columns found:", result.keys())
        
        row = result.fetchone()
        if row:
            print("First row SAMPLE:", row)

if __name__ == "__main__":
    debug_cols()
