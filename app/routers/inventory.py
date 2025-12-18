from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
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

@router.post("/api/capture", response_model=schemas.InventoryCapture)
async def create_capture(
    request: Request,
    capture: schemas.InventoryCaptureCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user)
):
    
    # Optional: Server-side validation of time ranges logic?
    # For now, we trust the client's explicit 'out_of_range' flag if they confirmed it.
    
    db_capture = models.InventoryCapture(
        capture_type=capture.capture_type,
        article_code=capture.article_code,
        article_description=capture.article_description,
        batch=capture.batch,
        quantity=capture.quantity,
        capture_date=capture.capture_date,
        capture_time=capture.capture_time,
        out_of_range=capture.out_of_range,
        user_id=user.id
    )
    
    db.add(db_capture)
    db.commit()
    db.refresh(db_capture)
    return db_capture
