import json
from sqlalchemy import create_engine, text

PG_URL = "postgresql://app_user:production_password@192.168.1.79:5434/production_db"
pg_engine = create_engine(PG_URL)

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

with pg_engine.connect() as conn:
    dispatches = conn.execute(text("SELECT id, document_ref, items_json FROM logistics_dispatch WHERE is_annulled = false")).fetchall()

# Collect all document numbers to check
docs_to_check = set()
dispatch_data = []

for dispatch in dispatches:
    d_id = dispatch[0]
    guide_ref = dispatch[1]
    items_json = dispatch[2]
    try:
        items = json.loads(items_json)
    except:
        continue
        
    for item in items:
        fact = item.get('fact', '').strip()
        if not fact or 'Manual' in fact:
            continue
            
        # Fact is already just the specific FACT:14764 or 14764 inside the JSON object
        clean_doc = fact.split('-')[-1].split(':')[-1].strip()
        docs_to_check.add(clean_doc)
        
        dispatch_data.append({
            'dispatch_id': d_id,
            'guide_ref': guide_ref,
            'doc_num': clean_doc,
            'item_desc': item.get('item', '').strip(),
            'qty': float(item.get('qty', 0)),
            'total_cajas': float(item.get('total_cajas', 0))
        })

print(f"Found {len(docs_to_check)} unique documents to verify.")

profit_data = {}
if docs_to_check:
    doc_list = "', '".join(docs_to_check)
    with profit_engine.connect() as profit_conn:
        sql = text(f"""
            SELECT R.doc_num, LTRIM(RTRIM(A.art_des)) as art_des, SUM(R.total_art) as qty,
                   CAST(SUM(ISNULL(R.total_art / NULLIF(U.equivalencia, 0), 0)) AS DECIMAL(18,2)) as cajas
            FROM saFacturaVentaReng R
            JOIN saArticulo A ON R.co_art = A.co_art
            LEFT JOIN saArtUnidad U ON A.co_art = U.co_art AND U.co_uni = 'CAJ'
            WHERE R.doc_num IN ('{doc_list}')
            GROUP BY R.doc_num, LTRIM(RTRIM(A.art_des))
            
            UNION ALL
            
            SELECT R.doc_num, LTRIM(RTRIM(A.art_des)) as art_des, SUM(R.total_art) as qty,
                   CAST(SUM(ISNULL(R.total_art / NULLIF(U.equivalencia, 0), 0)) AS DECIMAL(18,2)) as cajas
            FROM saNotaEntregaVentaReng R
            JOIN saArticulo A ON R.co_art = A.co_art
            LEFT JOIN saArtUnidad U ON A.co_art = U.co_art AND U.co_uni = 'CAJ'
            WHERE R.doc_num IN ('{doc_list}')
            GROUP BY R.doc_num, LTRIM(RTRIM(A.art_des))
        """)
        result = profit_conn.execute(sql).fetchall()
        for row in result:
            doc = row[0].strip()
            desc = row[1]
            qty = float(row[2])
            cajas = float(row[3]) if row[3] is not None else 0.0
            key = f"{doc}|{desc}"
            profit_data[key] = {'qty': qty, 'cajas': cajas}

print("Verification results:")
errors = []
perfects = 0
for d in dispatch_data:
    key = f"{d['doc_num']}|{d['item_desc']}"
    
    # Extract clean guide number for display rather than the whole string
    display_ref = d['guide_ref'].split('|')[0].strip()
    
    if key in profit_data:
        p_qty = profit_data[key]['qty']
        p_cajas = profit_data[key]['cajas']
        if abs(p_qty - d['qty']) > 0.01:
            errors.append(f"- **Guía {display_ref}**, Factura **{d['doc_num']}**: Artículo `{d['item_desc']}`\n  *Despachado en Guía*: {d['qty']} Unidades ({d['total_cajas']} Cajas)  |  *Real en Profit*: {p_qty} Unidades ({p_cajas} Cajas)")
        else:
            perfects += 1
    else:
        # Partial match fallback
        matched_qty = None
        matched_cajas = None
        for p_key, p_val in profit_data.items():
            if p_key.startswith(f"{d['doc_num']}|") and d['item_desc'][:15] in p_key:
                matched_qty = p_val['qty']
                matched_cajas = p_val['cajas']
                break
        
        if matched_qty is not None:
            if abs(matched_qty - d['qty']) > 0.01:
                errors.append(f"- **Guía {display_ref}**, Factura **{d['doc_num']}**: Artículo `{d['item_desc']}`\n  *Despachado en Guía*: {d['qty']} Unidades ({d['total_cajas']} Cajas)  |  *Real en Profit*: {matched_qty} Unidades ({matched_cajas} Cajas)")
            else:
                perfects += 1

print("\n--- FINAL DISCREPANCIES ---")
for e in errors:
    print(e)
print(f"\nTotal Errors found: {len(errors)}")
