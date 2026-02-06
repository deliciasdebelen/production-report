
from app.database import SessionLocal
from sqlalchemy import text

def check_schema():
    db = SessionLocal()
    try:
        print("--- TABLE LIST ---")
        # SQLite specific
        tables = db.execute(text("SELECT name FROM sqlite_master WHERE type='table';")).fetchall()
        for t in tables:
            print(t[0])
            
        print("--- END ---")

    finally:
        db.close()

if __name__ == "__main__":
    check_schema()
