from app.database import SessionLocal
from app import models
from sqlalchemy import func

def debug_visor():
    db = SessionLocal()
    print("--- DEBUG VISOR ---")
    
    # 1. Pending Planning
    try:
        pending = db.query(models.ProductionPlanning).filter(
            models.ProductionPlanning.status == 'Pending'
        ).all()
        print(f"Pending Planning: {len(pending)} items")
        for p in pending[:3]:
            print(f" - {p.order_number}: {p.article} ({p.status})")
    except Exception as e:
        print(f"Error querying Planning: {e}")

    # 2. Recent Production
    try:
        production = db.query(models.ProductionReport).order_by(
            models.ProductionReport.created_at.desc()
        ).limit(20).all()
        print(f"Recent Production: {len(production)} items")
        for r in production[:3]:
            print(f" - {r.order_number}: {r.article_type}")
    except Exception as e:
        print(f"Error querying Production: {e}")

    # 3. Logistics Reception
    try:
        receptions = db.query(
            models.LogisticsReceptionProduction, 
            models.ProductionReport.color, 
            models.ProductionReport.order_number
        ).join(
            models.ProductionReport, 
            models.LogisticsReceptionProduction.production_report_id == models.ProductionReport.id
        ).all()
        print(f"Receptions: {len(receptions)} items")
    except Exception as e:
        print(f"Error querying Receptions: {e}")
        
    db.close()

if __name__ == "__main__":
    debug_visor()
