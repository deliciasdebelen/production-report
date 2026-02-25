from app.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE inventory_captures ADD COLUMN department VARCHAR"))
            print("Added department column to inventory_captures")
        except Exception as e:
            if "duplicate column name" in str(e):
                print("Column department already exists")
            else:
                print(f"Error: {e}")

if __name__ == "__main__":
    migrate()
