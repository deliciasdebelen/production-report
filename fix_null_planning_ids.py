from app.database import SessionLocal
from app import models

db = SessionLocal()

print("Checking for existing max order number...")
existing = db.query(models.ProductionPlanning).filter(models.ProductionPlanning.order_number != None).count()
print(f"Found {existing} records with valid order_number.")

# Fetch Nulls
null_plans = db.query(models.ProductionPlanning).filter(models.ProductionPlanning.order_number == None).order_by(models.ProductionPlanning.id).all()

count = 0
for p in null_plans:
    # Strategy: Use ID as the order number source, assuming these are the first ones
    new_id = str(p.id).zfill(8)
    p.order_number = new_id
    print(f"Updating ID {p.id} -> Order #{new_id}")
    count += 1

if count > 0:
    db.commit()
    print(f"Successfully backfilled {count} records.")
else:
    print("No records to update.")

db.close()
