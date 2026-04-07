import json
from sqlalchemy import create_engine, text

pg_engine = create_engine("postgresql://app_user:production_password@192.168.1.79:5434/production_db")
with pg_engine.connect() as pg_conn:
    row = pg_conn.execute(text("SELECT document_ref, items_json FROM logistics_dispatch WHERE id = 21")).fetchone()
    if row:
        print(row[0])
        print(json.dumps(json.loads(row[1]), indent=2))
