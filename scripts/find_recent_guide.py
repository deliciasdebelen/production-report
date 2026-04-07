import json
from sqlalchemy import create_engine, text

PG_URL = "postgresql://app_user:production_password@192.168.1.79:5434/production_db"
pg_engine = create_engine(PG_URL)

with pg_engine.connect() as conn:
    dispatches = conn.execute(text("SELECT id, document_ref, items_json FROM logistics_dispatch ORDER BY id DESC LIMIT 5")).fetchall()

for dispatch in dispatches:
    d_id = dispatch[0]
    guide_ref = dispatch[1]
    print(f"\nGuide ID: {d_id} | Ref: {guide_ref}")
    try:
        items = json.loads(dispatch[2])
        for item in items:
            print(f"  Item: {item.get('item', '')}")
            print(f"    Qty: {item.get('qty', 0)} | Boxes: {item.get('total_cajas', 0)}")
    except:
        pass
