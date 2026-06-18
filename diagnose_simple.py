
from app.database import SessionLocal
from app.models import ProductionReport
from sqlalchemy import desc
import datetime

db = SessionLocal()
try:
    print(f"--- PRODUCTION REPORT DIAGNOSTIC ---")
    items = db.query(ProductionReport).order_by(desc(ProductionReport.created_at)).limit(20).all()
    for i in items:
        # Use str() to avoid format errors
        created = str(i.created_at)
        print(f"ID: {i.id} | Date: {created} | Status: {i.status} | Order: {i.order_number}")
    
    if not items:
        print("No Production Reports found.")

except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
