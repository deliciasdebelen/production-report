import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.external_db import create_engine_for_db
from sqlalchemy import text

def create_v2_sp(db_name, script_path):
    engine = create_engine_for_db(db_name)
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        with engine.begin() as conn:
            conn.execute(text(sql_script))
            print(f"Successfully created SP in {db_name}.")
    except Exception as e:
        print(f"Error executing script in {db_name}: {e}")

if __name__ == "__main__":
    create_v2_sp('carmal_a', 'sp_v2_create.sql')
