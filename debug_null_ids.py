from app.database import SessionLocal
from app import models
from sqlalchemy import text

db = SessionLocal()

print("--- PLANNING ORDERS WITH NULL ORDER_NUMBER ---")
planning_nulls = db.query(models.ProductionPlanning).filter(models.ProductionPlanning.order_number == None).all()
for p in planning_nulls:
    print(f"ID: {p.id}, Date: {p.date}, Status: {p.status}")

print("\n--- PRODUCTION REPORTS WITH NULL ORDER_NUMBER ---")
production_nulls = db.query(models.ProductionReport).filter(models.ProductionReport.order_number == None).all()
for p in production_nulls:
    print(f"ID: {p.id}, Date: {p.created_at}, Article: {p.article_type}")

print("\n--- TOTAL COUNTS ---")
print(f"Planning Nulls: {len(planning_nulls)}")
print(f"Production Nulls: {len(production_nulls)}")

db.close()
