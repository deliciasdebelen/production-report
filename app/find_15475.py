import sys
import os
sys.path.append('/app')
from app.database import SessionLocal
from app.models import LogisticsDispatch
import json

db = SessionLocal()
results = db.query(LogisticsDispatch).all()

for r in results:
    if not r.items_json: continue
    try:
        items = json.loads(r.items_json)
    except:
        continue
    
    invoices = []
    lines_for_15475 = []
    for item in items:
        fact = item.get('fact')
        if fact and "15475" in fact:
            invoices.append(fact)
            lines_for_15475.append(item)
            
    if invoices:
        print(f"Guide ID: {r.id}, REF: {r.document_ref}")
        print(f"Found {len(invoices)} lines for '15475':")
        for line in lines_for_15475:
            print(f" - {line.get('item')} | QTY: {line.get('qty')}")
        print("-" * 50)
