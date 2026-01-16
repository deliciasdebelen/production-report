from fastapi import APIRouter, Depends, Request, HTTPException
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
async def view_inventory(request: Request, user: models.User = Depends(get_current_active_user)):
    return templates.TemplateResponse("inventory.html", {"request": request, "title": "Inventario", "user": user})

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
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user)
):
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
    db.refresh(header)
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
