
from app.database import SessionLocal
from app import models
from app.utils_id import get_next_order_number

def inspect():
    db = SessionLocal()
    try:
        print("--- INSPECTION REPORT ---")
        
        # 1. Planning
        count_plan = db.query(models.ProductionPlanning).count()
        next_plan = get_next_order_number(db, models.ProductionPlanning)
        print(f"Planning: Count={count_plan}, NextID={next_plan}")
        
        if count_plan > 0:
             # Sample IDs
             ids = db.query(models.ProductionPlanning.order_number).limit(5).all()
             print(f"  Sample Planning IDs: {[i[0] for i in ids]}")

        # 2. Production
        count_prod = db.query(models.ProductionReport).count()
        next_prod = get_next_order_number(db, models.ProductionReport)
        print(f"Production: Count={count_prod}, NextID={next_prod}")

        if count_prod > 0:
             ids = db.query(models.ProductionReport.order_number).limit(5).all()
             print(f"  Sample Production IDs: {[i[0] for i in ids]}")

    finally:
        db.close()

if __name__ == "__main__":
    inspect()
