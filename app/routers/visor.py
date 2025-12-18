from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app import models, schemas
from datetime import date

router = APIRouter(
    prefix="/api/visor",
    tags=["visor"],
    responses={404: {"description": "Not found"}},
)

@router.get("/dashboard-data")
async def get_dashboard_data(db: Session = Depends(get_db)):
    # Tablero 1: Pendientes (Planning status='Pending')
    pending_planning = db.query(models.ProductionPlanning).filter(
        models.ProductionPlanning.status == 'Pending'
    ).order_by(models.ProductionPlanning.date.asc()).all()

    # Tablero 2: Procesadas (Production status='Confirmed' or just all production)
    # We assume 'Confirmed' roughly maps to existing Production Reports, or we filter by date
    today = date.today().strftime("%Y-%m-%d")
    recent_production = db.query(models.ProductionReport).order_by(
        models.ProductionReport.created_at.desc()
    ).limit(20).all()

    # Tablero 3: Indice (Planning vs Producion Not Processed) -- Backlog
    # Logic: Planning items older than today that are still Pending
    backlog = db.query(models.ProductionPlanning).filter(
        models.ProductionPlanning.status == 'Pending',
        models.ProductionPlanning.date < today
    ).all()

    return {
        "pending": pending_planning,
        "processed": recent_production,
        "backlog": backlog,
        "timestamp": date.today().isoformat()
    }
