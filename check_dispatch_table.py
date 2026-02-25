
from app.database import SessionLocal
from sqlalchemy import text

def check_info():
    db = SessionLocal()
    try:
        print("--- TABLE INFO logistics_dispatch ---")
        cols = db.execute(text("PRAGMA table_info(logistics_dispatch)")).fetchall()
        for c in cols:
             print(f"{c[1]} ({c[2]})")

        print("\n--- TABLE INFO logistics_routes ---")
        cols = db.execute(text("PRAGMA table_info(logistics_routes)")).fetchall()
        for c in cols:
             print(f"{c[1]} ({c[2]})")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_info()
