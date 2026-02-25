
from app.database import SessionLocal
from sqlalchemy import text

def check_info():
    db = SessionLocal()
    try:
        print("--- TABLE INFO production_reports ---")
        cols = db.execute(text("PRAGMA table_info(production_reports)")).fetchall()
        for c in cols:
             print(f"{c[1]} ({c[2]})")

        print("--- TABLE INFO logistics_reception_production ---")
        cols = db.execute(text("PRAGMA table_info(logistics_reception_production)")).fetchall()
        for c in cols:
             print(f"{c[1]} ({c[2]})")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_info()
