import sys
import os
sys.path.append('/app')
from app.database import SessionLocal
from app.models import LogisticsDispatch
import json

db = SessionLocal()
results = db.query(LogisticsDispatch).filter(LogisticsDispatch.document_ref.like('%168%')).all()

for r in results:
    print(f"ID: {r.id}, REF: {r.document_ref}, ANNULLED: {r.is_annulled}")
    items = json.loads(r.items_json)
    print(f"Items count: {len(items)}")
    
    invoices = []
    for item in items:
        fact = item.get('fact')
        if fact:
            invoices.append(fact)
            
    print(f"Invoices in guide: {invoices}")
    import collections
    duplicates = [item for item, count in collections.Counter(invoices).items() if count > 1]
    if duplicates:
        print(f"DUPLICATE INVOICES FOUND IN ITEMS: {duplicates}")
        
    print("-" * 50)
