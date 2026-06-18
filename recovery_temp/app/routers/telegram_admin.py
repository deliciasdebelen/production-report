# app/routers/telegram_admin.py
# Panel Administrativo para gestión de suscriptores Telegram.
# Solo accesible para Administradores (role == 4).

from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..dependencies import get_db, templates, get_current_user, get_current_active_user
from ..models import User, TelegramSubscriber
from ..services.mp_alert_service import send_telegram_to

router = APIRouter(prefix="/telegram-admin", tags=["telegram_admin"])


# ── Schema ───────────────────────────────────────────────────────

class SubscriberCreate(BaseModel):
    name: str
    chat_id: str
    report_type: Optional[str] = "MP"
    is_active: Optional[bool] = True


class SubscriberUpdate(BaseModel):
    name: Optional[str] = None
    chat_id: Optional[str] = None
    report_type: Optional[str] = None
    is_active: Optional[bool] = None


# ── Vista principal ──────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def telegram_admin_view(request: Request, user: User = Depends(get_current_user)):
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login")
    if user.role != 4:
        return templates.TemplateResponse("403.html", {"request": request, "user": user})
    return templates.TemplateResponse("telegram_admin.html", {
        "request": request,
        "user": user,
        "title": "Admin Telegram"
    })


# ── API CRUD ─────────────────────────────────────────────────────

@router.get("/api/subscribers")
async def list_subscribers(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    if user.role != 4:
        raise HTTPException(403, "Solo administradores")
    subs = db.query(TelegramSubscriber).order_by(TelegramSubscriber.id.asc()).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "chat_id": s.chat_id,
            "report_type": s.report_type,
            "is_active": s.is_active,
            "created_at": s.created_at.isoformat() if s.created_at else None
        }
        for s in subs
    ]


@router.post("/api/subscribers")
async def create_subscriber(
    payload: SubscriberCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    if user.role != 4:
        raise HTTPException(403, "Solo administradores")
    
    # Limpiar el chat_id (quitar espacios, guiones, etc.)
    chat_id_clean = payload.chat_id.strip().replace(" ", "").replace("-", "")
    
    sub = TelegramSubscriber(
        name=payload.name.strip(),
        chat_id=chat_id_clean,
        report_type=payload.report_type or "MP",
        is_active=payload.is_active if payload.is_active is not None else True
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return {
        "id": sub.id,
        "name": sub.name,
        "chat_id": sub.chat_id,
        "report_type": sub.report_type,
        "is_active": sub.is_active
    }


@router.put("/api/subscribers/{sub_id}")
async def update_subscriber(
    sub_id: int,
    payload: SubscriberUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    if user.role != 4:
        raise HTTPException(403, "Solo administradores")
    
    sub = db.query(TelegramSubscriber).filter(TelegramSubscriber.id == sub_id).first()
    if not sub:
        raise HTTPException(404, "Suscriptor no encontrado")
    
    if payload.name is not None:
        sub.name = payload.name.strip()
    if payload.chat_id is not None:
        sub.chat_id = payload.chat_id.strip().replace(" ", "")
    if payload.report_type is not None:
        sub.report_type = payload.report_type
    if payload.is_active is not None:
        sub.is_active = payload.is_active
    
    db.commit()
    db.refresh(sub)
    return {"id": sub.id, "name": sub.name, "chat_id": sub.chat_id,
            "report_type": sub.report_type, "is_active": sub.is_active}


@router.delete("/api/subscribers/{sub_id}")
async def delete_subscriber(
    sub_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    if user.role != 4:
        raise HTTPException(403, "Solo administradores")
    
    sub = db.query(TelegramSubscriber).filter(TelegramSubscriber.id == sub_id).first()
    if not sub:
        raise HTTPException(404, "Suscriptor no encontrado")
    
    db.delete(sub)
    db.commit()
    return {"status": "deleted", "id": sub_id}


@router.post("/api/test-send/{sub_id}")
async def test_send(
    sub_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    """Envía un mensaje de prueba al suscriptor indicado."""
    if user.role != 4:
        raise HTTPException(403, "Solo administradores")
    
    sub = db.query(TelegramSubscriber).filter(TelegramSubscriber.id == sub_id).first()
    if not sub:
        raise HTTPException(404, "Suscriptor no encontrado")
    
    from datetime import datetime
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
    mensaje = (
        f"✅ *PRUEBA DE CONEXIÓN — {ahora}*\n\n"
        f"Hola *{sub.name}*, este es un mensaje de prueba del sistema "
        f"*Delicias de Belén*.\n\n"
        f"📱 Chat ID: `{sub.chat_id}`\n"
        f"📋 Tipo de reporte: {sub.report_type}\n\n"
        f"_Si recibes este mensaje, la configuración es correcta._ ✔️"
    )
    
    ok = send_telegram_to(sub.chat_id, mensaje)
    return {
        "success": ok,
        "chat_id": sub.chat_id,
        "name": sub.name,
        "message": "Mensaje enviado correctamente" if ok else "Error al enviar (ver logs del servidor)"
    }


@router.post("/api/send-all-now")
async def send_all_now(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    """Dispara el reporte MP a todos los suscriptores activos ahora mismo."""
    if user.role != 4:
        raise HTTPException(403, "Solo administradores")
    
    from ..external_db import SessionA
    from ..services.mp_alert_service import (
        get_mp_demand, get_mp_purchases, calculate_mp_balance,
        send_mp_alert_to_all
    )
    from datetime import date
    
    hoy = date.today()
    fi = hoy.replace(day=1).isoformat()
    ff = hoy.isoformat()
    
    try:
        ext_session = SessionA()
        raw_conn = ext_session.get_bind().connect()
        demand = get_mp_demand(raw_conn, fi, ff)
        purchases = get_mp_purchases(raw_conn, fi, ff)
        raw_conn.close()
        ext_session.close()
    except Exception as e:
        return {"success": False, "error": f"Error consultando SQL Server: {str(e)}"}
    
    balance = calculate_mp_balance(demand, purchases)
    result = send_mp_alert_to_all(db, balance, hoy.strftime("%d/%m/%Y"))
    return {"success": True, "result": result, "articulos_analizados": len(balance)}
