"""
Inner script that runs inside the production Docker container.
Queries PostgreSQL for all logistics_dispatch records and prints JSON.
"""
import sys
sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models import LogisticsDispatch
import json

db = SessionLocal()
rows = db.query(
    LogisticsDispatch.id,
    LogisticsDispatch.document_ref,
    LogisticsDispatch.client_destination,
    LogisticsDispatch.date
).order_by(LogisticsDispatch.id).all()

data = []
for r in rows:
    data.append({
        'id': r.id,
        'ref': r.document_ref,
        'client': r.client_destination,
        'date': str(r.date)
    })

print(json.dumps(data))
db.close()
