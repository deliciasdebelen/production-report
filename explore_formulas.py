import asyncio
from sqlalchemy import text
from app.external_db import SessionM

def explore_profit_formulas():
    db = SessionM()
    try:
        query_formula = text("SELECT TOP 5 co_for, co_art, cantMax, cantMin, fpredeterminada FROM NSPFormula")
        print("--- TOP 5 NSPFormula ---")
        for r in db.execute(query_formula).fetchall():
            print(r)
            
        print("\n--- TOP 5 NSPFormulareng ---")
        query_reng = text("SELECT TOP 5 co_for, reng_num, co_art, cantidad, co_uni FROM NSPFormulareng")
        for r in db.execute(query_reng).fetchall():
            print(r)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    explore_profit_formulas()
