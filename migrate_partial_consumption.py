
from app.database import SessionLocal, engine
from app import models
from sqlalchemy import text

def migrate():
    print("Running migration for Partial Consumption logic...")
    db = SessionLocal()
    
    # 1. Add Column if not exists (Catch error if exists)
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE production_planning ADD COLUMN units_pending INTEGER"))
            print("Added 'units_pending' column.")
    except Exception as e:
        print(f"Column might already exist: {e}")

    # 2. Backfill Logic
    plans = db.query(models.ProductionPlanning).all()
    count = 0
    for p in plans:
        if p.units_pending is None:
            if p.status == 'Processed':
                p.units_pending = 0
            else:
                p.units_pending = p.units
            count += 1
            
    db.commit()
    print(f"Backfilled {count} records with units_pending data.")
    db.close()

if __name__ == "__main__":
    migrate()
