from app.database import SessionLocal
from app import models

db = SessionLocal()
try:
    print("Counting reports...")
    count = db.query(models.ProductionReport).count()
    print(f"Total reports: {count}")
    
    print("Fetching latest by ID desc...")
    latest = db.query(models.ProductionReport).order_by(models.ProductionReport.id.desc()).first()
    if latest:
        print(f"Latest ID: {latest.id}")
        print(f"Latest Created: {latest.created_at}")
    else:
        print("No reports found.")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
