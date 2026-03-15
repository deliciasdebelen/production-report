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

def analyze():
    params = urllib.parse.quote_plus(conn_str)
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
    
    # Check concept types
    df_c = pd.read_sql("SELECT co_conce, des_conce, tipo FROM snconcep WHERE co_conce IN ('R005', 'E020')", engine)
    print("\n--- CONCEPTOS INFO ---")
    print(df_c)

    receipts = [15216, 15348, 15645, 15840, 16753]
    receipts_str = ",".join(map(str, receipts))
    
    # Check snnomi lines to see if there are aggregated tables or headers
    df = pd.read_sql(f"SELECT reci_num, reng_num, co_conce, tipo, monto, auxi_num FROM snnomi WHERE reci_num IN ({receipts_str}) AND co_conce = 'R005'", engine)
    print("\n--- LINEAS A MODIFICAR ---")
    print(df)
    
if __name__ == "__main__":
    analyze()
