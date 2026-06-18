
from app.database import SessionLocal
from app import models
from app.utils_id import get_next_order_number
from sqlalchemy import text

def test_reset():
    db = SessionLocal()
    try:
        print("--- START TEST ---")
        # 1. Clear Table
        print("Clearing ProductionPlanning table...")
        db.query(models.ProductionPlanning).delete()
        db.commit()
        
        # 2. Check Next ID (Should be 1)
        next_id = get_next_order_number(db, models.ProductionPlanning)
        print(f"Next ID (Empty Table): {next_id}")
        if next_id != 1:
            print("FAILURE: Should be 1")
        else:
            print("SUCCESS: Is 1")

        # 3. Insert Record with order_number 5
        print("Inserting record with order_number=5...")
        item = models.ProductionPlanning(
            order_number="00000005",
            date="2023-01-01",
            article="Test",
            presentation="Test",
        )
        db.add(item)
        db.commit()

        # 4. Check Next ID (Should be 6)
        next_id = get_next_order_number(db, models.ProductionPlanning)
        print(f"Next ID (After Insert 5): {next_id}")
        if next_id != 6:
            print("FAILURE: Should be 6")
        else:
            print("SUCCESS: Is 6")

        # 5. Delete Record
        print("Deleting record...")
        db.query(models.ProductionPlanning).delete()
        db.commit()

        # 6. Check Next ID (Should be 1)
        next_id = get_next_order_number(db, models.ProductionPlanning)
        print(f"Next ID (After Delete): {next_id}")
        if next_id != 1:
            print("FAILURE: Should be 1")
        else:
            print("SUCCESS: Is 1")

    finally:
        db.close()

if __name__ == "__main__":
    test_reset()
