
from app.database import SessionLocal
from sqlalchemy import text

def migrate():
    db = SessionLocal()
    try:
        print("Adding 'status' column to logistics_reception_production...")
        db.execute(text("ALTER TABLE logistics_reception_production ADD COLUMN status VARCHAR DEFAULT 'Recepcionado'"))
        db.commit()
        print("Migration successful.")
    except Exception as e:
        print(f"Migration failed (maybe already exists?): {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
