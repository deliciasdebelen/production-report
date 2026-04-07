import json
from sqlalchemy import create_engine, text

# 1. Connect to PostgreSQL (App DB)
PG_URL = "postgresql://app_user:production_password@192.168.1.79:5434/production_db"
pg_engine = create_engine(PG_URL)

with pg_engine.connect() as conn:
    dispatches = conn.execute(text("SELECT id, document_ref, items_json FROM logistics_dispatch WHERE is_annulled = false")).fetchall()

# 2. Connect to SQL Server (Profit Plus)
PROFIT_URL = (
    "mssql+pyodbc:///?odbc_connect="
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.1.205;"
    "DATABASE=carmal_a;"
    "UID=PROFIT;"
    "PWD=profit;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)
profit_engine = create_engine(PROFIT_URL)

print("Starting dispatch vs invoice quantity audit...\n")
mismatches = []
total_items_checked = 0

with profit_engine.connect() as profit_conn:
    for dispatch in dispatches:
        dispatch_id = dispatch[0]
        guide_ref = dispatch[1]
        items_json = dispatch[2]
        
        try:
            items = json.loads(items_json)
        except:
            continue
            
        for item in items:
            total_items_checked += 1
            doc_num = item.get('fact', '').strip()
            item_desc = item.get('item', '').strip()
            dispatched_qty = float(item.get('qty', 0))
            
            if not doc_num or not item_desc:
                continue
                
            clean_doc = doc_num.split('-')[-1].strip()
            
            # Fetch all items for this invoice if not cached
            sql = text("""
                SELECT R.total_art, LTRIM(RTRIM(A.art_des)) as art_des
                FROM saFacturaVentaReng R
                JOIN saArticulo A ON R.co_art = A.co_art
                WHERE R.doc_num LIKE :doc
                UNION ALL
                SELECT R.total_art, LTRIM(RTRIM(A.art_des)) as art_des
                FROM saNotaEntregaVentaReng R
                JOIN saArticulo A ON R.co_art = A.co_art
                WHERE R.doc_num LIKE :doc
            """)
            result = profit_conn.execute(sql, {"doc": f"%{clean_doc}%"}).fetchall()
            
            # Build Python dict map
            profit_items = {}
            for row in result:
                qty = float(row[0])
                desc = row[1]
                profit_items[desc] = qty
            
            # Check if item_desc exists
            if item_desc not in profit_items:
                # Try partial match fallback
                matched = False
                for p_desc in profit_items:
                    if item_desc[:15] in p_desc:
                        profit_qty = profit_items[p_desc]
                        if abs(profit_qty - dispatched_qty) > 0.01:
                            mismatches.append({"dispatch_id": dispatch_id, "guide_ref": guide_ref, "doc_num": doc_num, "item_desc": item_desc, "dispatched_qty": dispatched_qty, "profit_qty": profit_qty, "issue": f"Quantity mismatch! Dispatched: {dispatched_qty}, Profit: {profit_qty}"})
                        matched = True
                        break
                
                if not matched:
                    mismatches.append({"dispatch_id": dispatch_id, "guide_ref": guide_ref, "doc_num": doc_num, "item_desc": item_desc, "dispatched_qty": dispatched_qty, "profit_qty": "NOT FOUND", "issue": "Item completely missing from Profit Plus document"})
            else:
                profit_qty = profit_items[item_desc]
                if abs(profit_qty - dispatched_qty) > 0.01:
                    mismatches.append({"dispatch_id": dispatch_id, "guide_ref": guide_ref, "doc_num": doc_num, "item_desc": item_desc, "dispatched_qty": dispatched_qty, "profit_qty": profit_qty, "issue": f"Quantity mismatch! Dispatched: {dispatched_qty}, Profit: {profit_qty}"})

print(f"Audit Complete. Checked {total_items_checked} individual dispatched items.")
print(f"Found {len(mismatches)} mismatches.\n")

for m in mismatches:
    print(f"Dispatch DB ID: {m['dispatch_id']} | Guide: {m['guide_ref']} | Factura: {m['doc_num']}")
    print(f"  Item: {m['item_desc']}")
    print(f"  Issue: {m['issue']}\n")
