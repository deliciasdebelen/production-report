import pyodbc
import urllib.parse
from sqlalchemy import create_engine, text

# Connection Params (from external_db.py)
params = urllib.parse.quote_plus(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.1.205;"
    "DATABASE=carmal_a;"
    "UID=PROFIT;"
    "PWD=profit;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)
conn_str = f"mssql+pyodbc:///?odbc_connect={params}"
engine = create_engine(conn_str)

def test_sp():
    with engine.connect() as conn:
        print("--- 1. Getting a valid Client ---")
        # Get a client to test with
        clis = conn.execute(text("SELECT TOP 1 co_cli, cli_des FROM sacliente WHERE inactivo=0")).fetchall()
        if not clis:
            print("No clients found.")
            return
        
        test_client = clis[0].co_cli.strip()
        print(f"Testing with Client: {test_client} ({clis[0].cli_des})")

        print("\n--- 2. Executing SP_CRM_FacturasPendientesPorCliente ---")
        try:
            # Note: Syntax depends on whether it's actually an SP or just a query the user wants.
            # Assuming SP.
            sql = text(f"EXEC SP_CRM_FacturasPendientesPorCliente @co_cli = :cli")
            result = conn.execute(sql, {"cli": test_client}).fetchall()
            
            if not result:
                print("SP returned no results (Client might have no pending invoices).")
                # Try to find a client WITH invoices if possible, or just print Schema if empty? 
                # Hard to print schema of empty result in SQLAlchemy text execution easily without cursor description.
                # Let's try raw pyodbc cursor for schema if empty.
            else:
                print(f"Got {len(result)} rows.")
                print("Columns found based on first row keys:")
                print(result[0]._mapping.keys())
                print("First Row Data:")
                print(result[0])
                
        except Exception as e:
            print(f"Error executing SP: {e}")

if __name__ == "__main__":
    test_sp()
