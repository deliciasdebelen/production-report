"""
Inner script for Docker: Query inventory tables in production PostgreSQL.
"""
import sys
sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models import InventoryHeader, InventoryLine
import json

db = SessionLocal()

headers = db.query(InventoryHeader).order_by(InventoryHeader.id).all()
lines = db.query(InventoryLine).order_by(InventoryLine.id).all()

data = {
    'header_count': len(headers),
    'line_count': len(lines),
    'headers': [
        {
            'id': h.id,
            'correlative': h.correlative,
            'date': str(h.date),
            'status': h.status,
            'notes': h.notes
        }
        for h in headers
    ],
    'lines_sample': [
        {
            'id': l.id,
            'header_id': l.header_id,
            'article_code': l.article_code,
            'article_description': l.article_description,
            'quantity': float(l.quantity) if l.quantity else 0
        }
        for l in lines[:10]
    ]
}

print(json.dumps(data))
db.close()
