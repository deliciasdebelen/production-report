from sqlalchemy import create_engine, text
import urllib.parse
from datetime import datetime

# Connection string for Profit Plus (SQL Server) - carmal_m (Manufacturing)
RAW_CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.1.205;"
    "DATABASE=carmal_m;"
    "UID=PROFIT;"
    "PWD=profit;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)
params_m = urllib.parse.quote_plus(RAW_CONN_STR)
db_url = f"mssql+pyodbc:///?odbc_connect={params_m}"

try:
    print(f"Connecting to carmal_m...")
    engine = create_engine(db_url)
    with engine.connect() as conn:
        print("Connected. Executing query...")
        sql = text("SELECT odp_num, fec_emis, cie_num FROM NSPCierreOP WHERE aju_num IS NULL")
        result = conn.execute(sql).fetchall()
        
        print(f"Found {len(result)} records.")
        
        today = datetime.now()
        days_threshold = 15
        
        for i, row in enumerate(result):
            if i >= 5: break # Show first 5
            
            d = dict(row._mapping)
            f_emis = d.get('fec_emis')
            aging = 0
            
            if f_emis:
                 if isinstance(f_emis, datetime):
                     aging = (today - f_emis).days
                 elif hasattr(f_emis, 'year'): # date
                     aging = (today.date() - f_emis).days
            
            print(f"Row {i}: Order={d['odp_num']}, Date={f_emis} (Age: {aging} days), Closure={d['cie_num']}")

except Exception as e:
    print(f"Error: {e}")
