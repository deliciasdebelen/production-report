import pyodbc
import pandas as pd
from sqlalchemy import create_engine
import urllib

conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.1.205;"
    "DATABASE=carmal_n;"
    "UID=PROFIT;"
    "PWD=profit;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

def fix_receipts():
    params = urllib.parse.quote_plus(conn_str)
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
    
    receipts = [15216, 15348, 15645, 15840, 16753]
    receipts_str = ",".join(map(str, receipts))
    
    # 1. Check snnomi
    df_nomi = pd.read_sql(f"SELECT reci_num, reng_num, co_conce, tipo, monto FROM snnomi WHERE reci_num IN ({receipts_str}) AND co_conce = 'R005'", engine)
    print("--- ANTES: snnomi ---")
    print(df_nomi)
    
    # 3. Apply fix
    print("\nApplying changes...")
    
    with engine.begin() as conn:
        from sqlalchemy import text
        # Update snnomi
        conn.execute(text(f"""
            UPDATE snnomi 
            SET co_conce = 'E020', tipo = 2
            WHERE reci_num IN ({receipts_str}) AND co_conce = 'R005'
        """))
    
    print("Changes applied successfully.")
    
    # 4. Verify snnomi
    df_nomi_after = pd.read_sql(f"SELECT reci_num, reng_num, co_conce, tipo, monto FROM snnomi WHERE reci_num IN ({receipts_str}) AND co_conce = 'E020'", engine)
    print("\n--- DESPUES: snnomi (E020) ---")
    print(df_nomi_after)

if __name__ == "__main__":
    fix_receipts()
