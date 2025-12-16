from fastapi import APIRouter, Depends, HTTPException, Request, Form
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
import json
from datetime import datetime

from ..dependencies import get_db, templates, get_current_user
from ..models import LogisticsReceptionProduction, LogisticsReceptionMerchandise, LogisticsDispatch, User

router = APIRouter(
    prefix="/logistics",
    tags=["logistics"],
    responses={404: {"description": "Not found"}},
)

# --- Views ---

@router.get("/")
async def logistics_dashboard(request: Request, user: User = Depends(get_current_user)):
    if user.role not in [1, 3, 4]: # Logic/Admin/Planner roles
        raise HTTPException(status_code=403, detail="Not authorized")
    return templates.TemplateResponse("logistics/dashboard.html", {
        "request": request,
        "user": user,
        "title": "Logística"
    })

@router.get("/reception/production")
async def view_reception_production(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    logs = db.query(LogisticsReceptionProduction).order_by(desc(LogisticsReceptionProduction.date)).limit(50).all()
    return templates.TemplateResponse("logistics/reception_production.html", {
        "request": request, 
        "user": user, 
        "logs": logs,
        "title": "Recepción de Producción"
    })

@router.get("/reception/merchandise")
async def view_reception_merchandise(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    logs = db.query(LogisticsReceptionMerchandise).order_by(desc(LogisticsReceptionMerchandise.date)).limit(50).all()
    # Parse JSON items for display
    for log in logs:
        try:
            log.items = json.loads(log.items_json)
        except:
            log.items = []
            
    return templates.TemplateResponse("logistics/reception_merchandise.html", {
        "request": request, 
        "user": user, 
        "logs": logs,
        "title": "Recepción de Mercancía"
    })

@router.get("/dispatch")
async def view_dispatch(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    logs = db.query(LogisticsDispatch).order_by(desc(LogisticsDispatch.date)).limit(50).all()
    for log in logs:
        try:
            log.items = json.loads(log.items_json)
        except:
            log.items = []

    return templates.TemplateResponse("logistics/dispatch.html", {
        "request": request, 
        "user": user, 
        "logs": logs,
        "title": "Despacho de Mercancía"
    })

# --- API Actions ---

# ... existing code ...

@router.get("/api/production/pending")
async def get_pending_production(
    order_id: Optional[str] = None,
    date_start: Optional[str] = None,
    date_end: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    query = db.query(models.ProductionReport).filter(models.ProductionReport.status == "Pending")
    
    if order_id:
        query = query.filter(models.ProductionReport.order_number.contains(order_id))
    
    if date_start:
        try:
            # Assume YYYY-MM-DD coming from frontend date input
            d_start = datetime.strptime(date_start, "%Y-%m-%d")
            query = query.filter(models.ProductionReport.created_at >= d_start)
        except ValueError:
            pass # Ignore invalid dates
            
    if date_end:
        try:
            d_end = datetime.strptime(date_end, "%Y-%m-%d")
            # Set to end of day
            d_end = d_end.replace(hour=23, minute=59, second=59)
            query = query.filter(models.ProductionReport.created_at <= d_end)
        except ValueError:
            pass

    reports = query.order_by(models.ProductionReport.created_at.desc()).all()
    return reports

@router.post("/reception/confirm")
async def confirm_reception(
    production_id: str = Form(...),
    received_qty: int = Form(...), # Received Units
    alert_email: Optional[str] = Form(None), # If discrepancy, send here
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    report = db.query(models.ProductionReport).filter(models.ProductionReport.id == production_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    # 1. Validation
    # logic: compare report.pt_units with received_qty
    discrepancy = report.pt_units - received_qty
    
    if discrepancy != 0:
        # 2. Email Alert Logic (Mock)
        if alert_email:
            print(f"--- [MOCK EMAIL] ---")
            print(f"To: {alert_email}")
            print(f"Subject: Alerta de Merma - Orden {report.order_number}")
            print(f"Body: Se detectó una diferencia de {discrepancy} unidades en la recepción de la orden {report.order_number}.")
            print(f"--------------------")
    
    # 3. Update Status
    report.status = "Confirmed"
    
    # 4. Log the Reception event
    # Calculate boxes/kg for the log based on received_qty
    # We need to reuse the presentation logic or just store raw units for now. 
    # Let's simple-store raw units.
    
    new_log = LogisticsReceptionProduction(
        production_report_id=report.id,
        product_name=report.article_type, # Using article name
        quantity=received_qty,
        notes=f"Recibido por {user.username}. Diferencia: {discrepancy}"
    )
    db.add(new_log)
    db.commit()
    
    return {"status": "success", "discrepancy": discrepancy}

# ... existing dispatch ...

@router.post("/reception/merchandise")
async def create_reception_merchandise(
    supplier: str = Form(...),
    document_ref: str = Form(...),
    items: str = Form(...), # JSON string
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_log = LogisticsReceptionMerchandise(
        supplier=supplier,
        document_ref=document_ref,
        items_json=items
    )
    db.add(new_log)
    db.commit()
    return {"status": "success"}

@router.post("/dispatch")
async def create_dispatch(
    client_destination: str = Form(...),
    document_ref: str = Form(...),
    items: str = Form(...), # JSON string
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_log = LogisticsDispatch(
        client_destination=client_destination,
        document_ref=document_ref,
        items_json=items
    )
    db.add(new_log)
    db.commit()
    return {"status": "success"}
