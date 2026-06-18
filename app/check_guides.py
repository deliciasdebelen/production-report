import sys
sys.path.append('/app')
from app.database import SessionLocal
from app.models import LogisticsDispatch

db = SessionLocal()
last_dispatches = db.query(LogisticsDispatch).order_by(LogisticsDispatch.id.desc()).limit(10).all()

for r in last_dispatches:
    print(f"ID: {r.id}, REF: {r.document_ref}")
