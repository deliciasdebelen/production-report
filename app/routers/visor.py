from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app import models, schemas
from datetime import date, datetime

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

    # Tablero 2: Procesadas (Production status='Confirmed')
    # Limit to today or recent
    recent_production = db.query(models.ProductionReport).order_by(
        models.ProductionReport.created_at.desc()
    ).limit(20).all()

    # Tablero 3: Recepcion Logistica (De Produccion)
    # Join with ProductionReport to get the Color
    receptions = db.query(
        models.LogisticsReceptionProduction, 
        models.ProductionReport.color, 
        models.ProductionReport.order_number,
        models.ProductionReport.status
    ).join(
        models.ProductionReport, 
        models.LogisticsReceptionProduction.production_report_id == models.ProductionReport.id
    ).order_by(models.LogisticsReceptionProduction.date.desc()).limit(20).all()

    # Format reception for frontend
    reception_data = []
    for r, color, order_num, status in receptions:
        reception_data.append({
            "id": r.id,
            "product_name": r.product_name,
            "quantity": r.quantity,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "color": color,
            "order_number": order_num,
            "status": status
        })

    # Format Pending for frontend
    pending_data = [{
        "id": p.id,
        "order_number": p.order_number,
        "date": p.date, # date is String in DB, no isoformat needed
        "article": p.article,
        "presentation": p.presentation,
        "batches": p.batches,
        "units": p.units,
        "units_pending": p.units_pending,
        "status": p.status
    } for p in pending_planning]

    # Format Processed for frontend
    processed_data = [{
        "id": r.id,
        "order_number": r.order_number,
        "date": r.created_at.isoformat() if r.created_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "article": r.article_type, 
        "article_type": r.article_type,
        "presentation": r.presentation, 
        "boxes": r.boxes,
        "pt_units": r.pt_units,
        "status": r.status
    } for r in recent_production]
    
    # Reception formatting already happened in loop above, but let's check it.
    # We constructed reception_data manually.
    # Let's add status to reception_data.
    # reception query: models.LogisticsReceptionProduction, color, order_number.
    # It doesn't fetch status. But reception implies "Received".
    # I can just hardcode "Recepcionado" or fetch report status.
    # The user wants "status of the document".
    # I'll update the loop below this replace block or just let frontend handle text for reception.
    
    return {
        "pending": pending_data,
        "processed": processed_data,
        "reception": reception_data,
        "timestamp": datetime.now().isoformat()
    }
