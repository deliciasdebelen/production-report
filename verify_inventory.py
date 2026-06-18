from app.database import SessionLocal
from app.models import InventoryCapture
from sqlalchemy import text

def verify():
    db = SessionLocal()
    try:
        # Check table
        print("Checking table existence...")
        db.execute(text("SELECT 1 FROM inventory_captures LIMIT 1"))
        print("Table exists.")

        # Test Insert
        print("Testing insert...")
        test_item = InventoryCapture(
            capture_type="Inicio",
            article_code="TEST-001",
            article_description="Test Item",
            batch="BATCH-001",
            quantity=100.0,
            capture_date="2025-12-17",
            capture_time="08:00",
            out_of_range=False,
            user_id=1
        )
        db.add(test_item)
        db.commit()
        
        # Read back
        inserted = db.query(InventoryCapture).filter_by(article_code="TEST-001").first()
        if inserted:
            print(f"Successfully inserted record ID: {inserted.id}")
            # Clean up
            db.delete(inserted)
            db.commit()
            print("Cleanup complete.")
        else:
            print("Failed to read back inserted record.")

    except Exception as e:
        print(f"Verification Failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify()
