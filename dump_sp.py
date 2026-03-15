import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.external_db import create_engine_for_db
from sqlalchemy import text

def dump_sp(db_name):
    engine = create_engine_for_db(db_name)
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT OBJECT_DEFINITION(OBJECT_ID('repformatofacturaventaOM_consolidada'))")).scalar()
            if result:
                with open(f'sp_dump_{db_name}.sql', 'w', encoding='utf-8') as f:
                    f.write(str(result))
                print(f"Found in {db_name} and dumped successfully.")
            else:
                print(f"Not found in {db_name}.")
    except Exception as e:
        print(f"Error accessing {db_name}: {e}")

if __name__ == "__main__":
    dump_sp('carmal_a')
    dump_sp('carmal_m')
