
from app.external_db import engine_a
from sqlalchemy import text
import sys

def deploy_sp():
    sp_file = "sp_definition.sql"
    try:
        with open(sp_file, 'r', encoding='utf-8') as f:
            sp_sql = f.read()
            
        print(f"Read {len(sp_sql)} bytes from {sp_file}")
        
        # Ensure it is ALTER
        if "CREATE PROCEDURE" in sp_sql:
            print("Converting CREATE to ALTER...")
            sp_sql = sp_sql.replace("CREATE PROCEDURE", "ALTER PROCEDURE")
            
        with engine_a.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            print("Executing SP update on database...")
            conn.exec_driver_sql(sp_sql)
            print("SP executed successfully.")
            
    except Exception as e:
        print(f"Error deploying SP: {e}")
        sys.exit(1)

if __name__ == "__main__":
    deploy_sp()
