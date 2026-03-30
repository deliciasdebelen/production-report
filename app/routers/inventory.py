from fastapi import APIRouter, Depends, Request, HTTPException, BackgroundTasks
from ..email_utils import send_email
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from .. import models, schemas
from ..dependencies import get_db, get_current_active_user, templates
from datetime import datetime

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"]
)

@router.get("/", response_class=HTMLResponse)
async def view_inventory(request: Request, db: Session = Depends(get_db), user: models.User = Depends(get_current_active_user)):
    next_correlative = generate_inventory_correlative(db)
    return templates.TemplateResponse("inventory.html", {"request": request, "title": "Inventario", "user": user, "next_correlative": next_correlative})

def generate_inventory_correlative(db: Session) -> str:
    # Format: INV-YYYYMMDD-XXXX (e.g., INV-20250620-0001)
    prefix = f"INV-{datetime.now().strftime('%Y%m%d')}"
    
    # Find last correlative with this prefix
    last = db.query(models.InventoryCaptureHeader)\
        .filter(models.InventoryCaptureHeader.correlative.like(f"{prefix}%"))\
        .order_by(models.InventoryCaptureHeader.id.desc())\
        .first()
    
    if last:
        # Extract last 4 digits
        try:
            last_seq = int(last.correlative.split('-')[-1])
            new_seq = last_seq + 1
        except:
            new_seq = 1
    else:
        new_seq = 1
        
    return f"{prefix}-{str(new_seq).zfill(4)}"

@router.post("/api/full-capture", response_model=schemas.InventoryHeader)
async def create_full_capture(
    data: schemas.InventoryHeaderCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user)
):
    # Role Check: KPI(1), Admin(4), Warehouse(5), Inventory(6)
    if user.role not in [1, 4, 5, 6]:
        raise HTTPException(status_code=403, detail="No tiene permisos para registrar inventario")

    # 1. Generate Correlative
    correlative = generate_inventory_correlative(db)
    
    # 2. Create Header
    header = models.InventoryCaptureHeader(
        correlative=correlative,
        date=data.date, # User-provided or current? Schema says user provided.
        user_id=user.id,
        status="Confirmed",
        notes=data.notes
    )
    db.add(header)
    db.flush() # Get ID
    
    # 3. Create Lines
    for line in data.lines:
        db_line = models.InventoryCaptureLine(
            header_id=header.id,
            article_code=line.article_code,
            article_description=line.article_description,
            batch=line.batch,
            quantity=line.quantity
        )
        db.add(db_line)
        
    db.commit()
    db.commit()
    db.refresh(header)

    # --- Email Notification ---
    try:
        subscribers = db.query(models.NotificationSubscriber).filter(
            models.NotificationSubscriber.report_type == 'Inventory',
            models.NotificationSubscriber.is_active == True
        ).all()
        
        if subscribers:
            recipients = [s.email for s in subscribers]
            subject = f"Nuevo Inventario Registrado: {correlative}"
            body = f"""
            <h3>Nuevo Registro de Inventario</h3>
            <p><strong>Correlativo:</strong> {correlative}</p>
            <p><strong>Fecha:</strong> {header.date}</p>
            <p><strong>Usuario:</strong> {user.username}</p>
            <p><strong>Registros:</strong> {len(data.lines)} ítems</p>
            <hr>
            <p><a href="http://192.168.1.18:8000/logistics/inventory">Ver en Sistema</a></p>
            """
            background_tasks.add_task(send_email, subject, body, recipients, is_html=True)
    except Exception as e:
        print(f"Error queuing email: {e}")

    return header

@router.get("/api/history", response_model=list[schemas.InventoryHeader])
def get_inventory_history(limit: int = 50, db: Session = Depends(get_db)):
    # Return recent headers with eager loading of lines if needed, or just headers first
    headers = db.query(models.InventoryCaptureHeader)\
        .order_by(desc(models.InventoryCaptureHeader.date))\
        .limit(limit)\
        .all()
    return headers

@router.get("/api/capture/{id}", response_model=schemas.InventoryHeader)
def get_capture_detail(id: int, db: Session = Depends(get_db)):
    header = db.query(models.InventoryCaptureHeader).filter(models.InventoryCaptureHeader.id == id).first()
    if not header:
        raise HTTPException(404, "Captura no encontrada")
    return header
