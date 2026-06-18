
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, text
from typing import Optional
from ..database import get_db
from ..external_db import get_external_db
from .. import models
from ..dependencies import get_current_active_user, templates
from datetime import datetime, timedelta

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    responses={404: {"description": "Not found"}},
)



def apply_date_filter(query, model, date_column, start_date: str, end_date: str):
    if start_date:
        query = query.filter(date_column >= start_date)
    if end_date:
        # If it's a string YYYY-MM-DD, strict comparison works. 
        # If it's datetime, we might need to add time for end_date to include the whole day.
        # Check models.py:
        # Planning: String YYYY-MM-DD
        # Production: DateTime
        # Logistics: DateTime
        # Inventory: String
        
        # For strings, it is direct.
        # For DateTime, end_date "2023-01-01" becomes "2023-01-01 00:00:00" usually.
        # So filtering <= end_date might miss records on that day if they have time.
        # We should filter < end_date + 1 day OR cast to date.
        
        # Let's try casting to date for DateTime columns.
        is_datetime = str(date_column.type).startswith("DATETIME")
        
        if is_datetime:
             query = query.filter(func.date(date_column) <= end_date)
             if start_date:
                 query = query.filter(func.date(date_column) >= start_date)
                 # Re-applying start because the generic 'if start_date' above might behave efficiently with raw generic filter
                 # but mixing generic >= with func.date <= is fine.
                 # ACTUALLY, let's just overload the generic logic with specific logic.
                 return query
        
        query = query.filter(date_column <= end_date)
        
    return query

@router.get("/planning")
async def report_planning(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = db.query(models.ProductionPlanning)
    
    if start_date:
        query = query.filter(models.ProductionPlanning.date >= start_date)
    if end_date:
        query = query.filter(models.ProductionPlanning.date <= end_date)
        
    items = query.order_by(desc(models.ProductionPlanning.date)).all()
    
    return templates.TemplateResponse("reports/planning.html", {
        "request": request,
        "items": items,
        "start_date": start_date,
        "end_date": end_date,
        "title": "Reporte de Planificación",
        "user": current_user
    })

@router.get("/production")
async def report_production(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = db.query(models.ProductionReport)
    
    if start_date:
        query = query.filter(func.date(models.ProductionReport.created_at) >= start_date)
    if end_date:
        query = query.filter(func.date(models.ProductionReport.created_at) <= end_date)
        
    items = query.order_by(desc(models.ProductionReport.created_at)).all()
    
    return templates.TemplateResponse("reports/production.html", {
        "request": request,
        "items": items,
        "start_date": start_date,
        "end_date": end_date,
        "title": "Reporte de Producción",
        "user": current_user
    })

@router.get("/logistics")
async def report_logistics(
    request: Request,
    active_tab: str = "reception_production",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Fetch data for ALL tabs or just the active one?
    # Usually better to fetch only active, but for simplicity/speed of switching tabs (client side), we might fetch all?
    # Or reload page on tab switch. Reload is cleaner for data querying.
    # User asked for "consulta de reportes para [list]", implies they want to see them.
    
    # Let's simplify: pass data for all if not too heavy, or make tabs link to ?active_tab=X
    
    items = []
    
    if active_tab == "reception_production":
        q = db.query(models.LogisticsReceptionProduction)
        if start_date: q = q.filter(func.date(models.LogisticsReceptionProduction.date) >= start_date)
        if end_date: q = q.filter(func.date(models.LogisticsReceptionProduction.date) <= end_date)
        items = q.order_by(desc(models.LogisticsReceptionProduction.date)).all()
        
    elif active_tab == "reception_merchandise":
        q = db.query(models.LogisticsReceptionMerchandise)
        if start_date: q = q.filter(func.date(models.LogisticsReceptionMerchandise.date) >= start_date)
        if end_date: q = q.filter(func.date(models.LogisticsReceptionMerchandise.date) <= end_date)
        items = q.order_by(desc(models.LogisticsReceptionMerchandise.date)).all()
        
    elif active_tab == "dispatch":
        q = db.query(models.LogisticsDispatch)
        if start_date: q = q.filter(func.date(models.LogisticsDispatch.date) >= start_date)
        if end_date: q = q.filter(func.date(models.LogisticsDispatch.date) <= end_date)
        items = q.order_by(desc(models.LogisticsDispatch.date)).all()
        
    elif active_tab == "inventory":
        q = db.query(models.InventoryCaptureHeader)
        if start_date: q = q.filter(models.InventoryCaptureHeader.date >= start_date)
        if end_date: q = q.filter(models.InventoryCaptureHeader.date <= end_date)
        items = q.order_by(desc(models.InventoryCaptureHeader.date)).all()

    return templates.TemplateResponse("reports/logistics.html", {
        "request": request,
        "items": items,
        "active_tab": active_tab,
        "start_date": start_date,
        "end_date": end_date,
        "title": "Reporte Logístico",
        "user": current_user
    })

@router.get("/inventory/physical-sheet")
def print_physical_sheet(
    request: Request,
    db_ext: Session = Depends(get_external_db)
):
    try:
        # Fetch Articles for Inventory Sheet (MP, ME, PT)
        sql = text("""
            SELECT 
                a.co_art as code,
                a.art_des as description,
                u.des_uni as unit
            FROM saArticulo a
            LEFT JOIN saartunidad au ON a.co_art = au.co_art AND au.equivalencia = 1
            LEFT JOIN saUnidad u ON au.co_uni = u.co_uni
            WHERE a.anulado = 0 AND a.co_lin IN ('MP', 'ME', 'PT')
            ORDER BY a.art_des
        """)
        result = db_ext.execute(sql).fetchall()
        
        articles = [
            {
                "code": str(row.code).strip(),
                "description": str(row.description).strip(),
                "unit": str(row.unit).strip() if row.unit else "N/A"
            }
            for row in result
        ]
    except Exception as e:
        print(f"Error fetching articles for sheet: {e}")
        articles = []

    return templates.TemplateResponse("logistics/print_inventory_sheet.html", {
        "request": request,
        "articles": articles
    })

@router.get("/inventory/print/{id}")
def print_inventory_record(
    id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    header = db.query(models.InventoryCaptureHeader).filter(models.InventoryCaptureHeader.id == id).first()
    if not header:
        # If not found, maybe redirect or 404. For now, 404.
        return templates.TemplateResponse("logistics/print_inventory_sheet.html", {
            "request": request,
            "error": "Documento no encontrado",
            "articles": [] 
        })
    
    return templates.TemplateResponse("logistics/print_inventory_sheet.html", {
        "request": request,
        "header": header
    })
