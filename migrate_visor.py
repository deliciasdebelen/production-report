from app.database import engine, Base
from sqlalchemy import text

def migrate_visor():
    with engine.connect() as conn:
        # Check if status column exists in production_planning
        try:
            result = conn.execute(text("PRAGMA table_info(production_planning)")).fetchall()
            columns = [row[1] for row in result]
            
            if 'status' not in columns:
                print("Adding 'status' column to production_planning...")
                conn.execute(text("ALTER TABLE production_planning ADD COLUMN status VARCHAR DEFAULT 'Pending'"))
                conn.commit()
                print("Migration successful: Added 'status' column.")
            else:
                print("Column 'status' already exists in production_planning.")
                
        except Exception as e:
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate_visor()
