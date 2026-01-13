import urllib.parse
from sqlalchemy import create_engine, text

# Connection Params (Confirmed from external_db.py)
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

def debug_client():
    target_client = "J411903523"
    print(f"--- Debugging Client: '{target_client}' ---")
    
    with engine.connect() as conn:
        # 1. Verify Client Exists in Table
        print("\n[Step 1] Checking sacliente table:")
        sql_check = text("SELECT co_cli, cli_des FROM sacliente WHERE co_cli = :cli")
        res_check = conn.execute(sql_check, {"cli": target_client}).fetchall()
        if res_check:
            print(f"  Found in DB: co_cli='{res_check[0].co_cli}', cli_des='{res_check[0].cli_des}'")
            print(f"  Raw co_cli: {repr(res_check[0].co_cli)}") # Check for hidden chars
        else:
            print("  Client NOT found in sacliente table (Wait, how did user select it?)")

        # 2. Execute SP
        print("\n[Step 2] Executing SP_CRM_FacturasPendientesPorCliente:")
        try:
            # Using exact same syntax as Backend
            sql_sp = text("EXEC SP_CRM_FacturasPendientesPorCliente @co_cli = :cli")
            
            # Attempt 1: Standard Binding
            print("  > Attempt 1 (Standard Binding):")
            res_sp = conn.execute(sql_sp, {"cli": target_client}).fetchall()
            print(f"    Rows returned: {len(res_sp)}")
            
            # Attempt 2: Hardcoded String (to rule out binding issues)
            print("  > Attempt 2 (Hardcoded String):")
            sql_hard = text(f"EXEC SP_CRM_FacturasPendientesPorCliente @co_cli = '{target_client}'")
            res_hard = conn.execute(sql_hard).fetchall()
            print(f"    Rows returned: {len(res_hard)}")
            
        except Exception as e:
            print(f"  Error executing SP: {e}")

if __name__ == "__main__":
    debug_client()
