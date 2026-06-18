from app.database import engine
from sqlalchemy import text

def upgrade():
    with engine.connect() as conn:
        try:
            print("Adding column mp_containers to production_reports...")
            conn.execute(text("ALTER TABLE production_reports ADD COLUMN mp_containers INTEGER DEFAULT 0"))
            print("Done.")
        except Exception as e:
            print(f"Error (maybe column exists?): {e}")

if __name__ == "__main__":
    upgrade()
