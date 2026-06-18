
from app.database import engine, SessionLocal
from app import models, schemas
from datetime import datetime

# 1. Create Tables
print("Creating tables if not exist...")
models.Base.metadata.create_all(bind=engine)

# 2. Test Logic
print("Testing Full Capture Logic...")
db = SessionLocal()

# Mock Data
try:
    # Need a user
    user = db.query(models.User).first()
    if not user:
        print("Creating mock user...")
        user = models.User(username="test_inv", password_hash="x", role=4)
        db.add(user)
        db.commit()

    # Generate Correlative Logic Check
    from app.routers.inventory import generate_inventory_correlative
    next_corr = generate_inventory_correlative(db)
    print(f"Generated Correlative Preview: {next_corr}")

    # Create Header directly to test model
    header = models.InventoryCaptureHeader(
        correlative=next_corr,
        date=datetime.now(),
        user_id=user.id,
        status="Confirmed"
    )
    db.add(header)
    db.flush()
    
    # Create Line
    line = models.InventoryCaptureLine(
        header_id=header.id,
        article_code="TST-01",
        article_description="Test Item",
        batch="B-001",
        quantity=100.0
    )
    db.add(line)
    db.commit()
    print(f"Successfully saved Capture #{header.id} with Correlative {header.correlative}")

    # Verify filtering
    saved = db.query(models.InventoryCaptureHeader).filter_by(id=header.id).first()
    print(f"Retrieved: {saved.correlative} - Lines: {len(saved.lines)}")

except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
