
from app.database import SessionLocal
from app.models import LogisticsReceptionProduction, LogisticsDispatch, InventoryCaptureHeader, ProductionReport, ProductionPlanning
from sqlalchemy import desc, func
import datetime

db = SessionLocal()
try:
    print(f"--- SERVER TIME DIAGNOSTIC ---")
    print(f"Local Time: {datetime.datetime.now()}")
    print("------------------------------")

    print("\n--- RECENT PRODUCTION REPORTS (Models.ProductionReport) ---")
    # Check the base production reports (maybe they were created but not received?)
    items = db.query(ProductionReport).order_by(desc(ProductionReport.created_at)).limit(10).all()
    for i in items:
        print(f"ID: {i.id} | Created: {i.created_at} | Status: {i.status} | Order: {i.order_number}")

    print("\n--- RECENT LOGISTICS RECEPTION (Models.LogisticsReceptionProduction) ---")
    items = db.query(LogisticsReceptionProduction).order_by(desc(LogisticsReceptionProduction.date)).limit(10).all()
    for i in items:
        print(f"ID: {i.id} | Date: {i.date} | Product: {i.product_name}")

    print("\n--- RECENT PRODUCTION PLANNING (Models.ProductionPlanning) ---")
    items = db.query(ProductionPlanning).order_by(desc(ProductionPlanning.date)).limit(10).all()
    for i in items:
        print(f"ID: {i.id} | Date: {i.date} | Order: {i.order_number}")

finally:
    db.close()
