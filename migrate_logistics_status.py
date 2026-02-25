from app.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        try:
            # Check if column exists
            result = conn.execute(text("SELECT status FROM logistics_reception_production")).fetchone()
            print("Column 'status' already exists.")
        except Exception:
            print("Column 'status' missing. Adding it...")
            try:
                # SQL Server syntax
                conn.execute(text("ALTER TABLE logistics_reception_production ADD status VARCHAR(50) DEFAULT 'Recepcionado'"))
                conn.commit()
                print("Migration successful.")
            except Exception as e:
                print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
