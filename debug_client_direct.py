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

def debug_direct():
    target = "J411903523" 
    print(f"--- Debugging Direct Query for {target} ---")
    
    with engine.connect() as conn:
        # 1. Exact Match
        sql = text("SELECT co_cli, cli_des FROM sacliente WHERE co_cli = :cli")
        res = conn.execute(sql, {"cli": target}).fetchall()
        print(f"1. Exact Match '{target}': {len(res)} rows")
        if res:
            print(f"   Val: '{res[0].co_cli}' (Len: {len(res[0].co_cli)})")
            
        # 2. Like Match
        sql_like = text("SELECT co_cli, cli_des FROM sacliente WHERE co_cli LIKE :cli")
        res_like = conn.execute(sql_like, {"cli": f"%{target}%"}).fetchall()
        print(f"2. LIKE Match '%{target}%': {len(res_like)} rows")
        for r in res_like:
            print(f"   Found: '{r.co_cli}' (Len: {len(r.co_cli)})")

if __name__ == "__main__":
    debug_direct()
