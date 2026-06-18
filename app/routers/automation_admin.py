from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..dependencies import get_db, templates, get_current_user, get_current_active_user
from ..models import User, ProfitAutomationConfig
from ..services.automation_scheduler import execute_openclaw_task, update_scheduler_cron

router = APIRouter(prefix="/automation-admin", tags=["automation_admin"])

class AutomationConfigUpdate(BaseModel):
    emails: str
    cron_schedule: str
    is_active: bool

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def automation_admin_view(request: Request, user: User = Depends(get_current_user)):
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login")
    if user.role != 4:
        return templates.TemplateResponse("403.html", {"request": request, "user": user})
    return templates.TemplateResponse("automation_admin.html", {
        "request": request,
        "user": user,
        "title": "Automatizaciones Profit"
    })

@router.get("/api/config")
async def get_config(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    if user.role != 4:
        raise HTTPException(403, "Solo administradores")
    
    config = db.query(ProfitAutomationConfig).first()
    if not config:
        config = ProfitAutomationConfig()
        db.add(config)
        db.commit()
        db.refresh(config)
        
    return {
        "id": config.id,
        "emails": config.emails,
        "cron_schedule": config.cron_schedule,
        "is_active": config.is_active
    }

@router.put("/api/config")
async def update_config(
    payload: AutomationConfigUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    if user.role != 4:
        raise HTTPException(403, "Solo administradores")
    
    config = db.query(ProfitAutomationConfig).first()
    if not config:
        config = ProfitAutomationConfig()
        db.add(config)
        
    config.emails = payload.emails
    config.cron_schedule = payload.cron_schedule
    config.is_active = payload.is_active
    
    db.commit()
    db.refresh(config)
    
    try:
        update_scheduler_cron(config.cron_schedule)
    except Exception as e:
        # We save it but warn the user
        return {"status": "saved", "warning": f"Cron mal formateado. Error: {e}"}
        
    return {
        "status": "success",
        "id": config.id,
        "emails": config.emails,
        "cron_schedule": config.cron_schedule,
        "is_active": config.is_active
    }

@router.post("/api/run-now")
async def run_now(
    user: User = Depends(get_current_active_user)
):
    if user.role != 4:
        raise HTTPException(403, "Solo administradores")
        
    result = execute_openclaw_task()
    
    if result.get("success"):
        return {"status": "success", "message": "Tarea ejecutada correctamente", "output": result.get("stdout")}
    else:
        raise HTTPException(500, detail=result.get("error") or result.get("stderr"))
