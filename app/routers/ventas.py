from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.dependencies import get_current_user, templates, get_db
from app import models
from sqlalchemy.orm import Session
from app.services import chatbot as chatbot_service

router = APIRouter(
    prefix="/ventas",
    tags=["ventas"]
)

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def view_ventas_dashboard(request: Request, user: models.User = Depends(get_current_user)):
    return templates.TemplateResponse("ventas/index.html", {
        "request": request,
        "title": "Ventas",
        "user": user
    })

@router.get("/chatbot", response_class=HTMLResponse)
async def view_chatbot_panel(request: Request, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return RedirectResponse(url="/login")
    if user.role not in [1, 4, 8, 9]: # Admin, KPI/Sales, Director, Soporte
        return templates.TemplateResponse("403.html", {"request": request, "user": user})

    config = chatbot_service.get_chatbot_config(db)
    return templates.TemplateResponse("ventas/chatbot.html", {
        "request": request,
        "title": "Chatbot Inteligente",
        "user": user,
        "config": config
    })

@router.post("/chatbot/save")
async def save_chatbot_settings(
    request: Request,
    db_host: str = Form(...),
    db_name: str = Form(...),
    db_user: str = Form(...),
    db_password: str = Form(...),
    whatsapp_number: str = Form(...),
    ai_provider: str = Form(...),
    gemini_api_key: str = Form(None),
    ollama_api_url: str = Form(...),
    whatsapp_gateway_url: str = Form(...),
    whatsapp_gateway_token: str = Form(None),
    is_active: bool = Form(False),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user.role not in [1, 4]:
        return RedirectResponse(url="/ventas", status_code=303)
        
    config = chatbot_service.get_chatbot_config(db)
    config.db_host = db_host
    config.db_name = db_name
    config.db_user = db_user
    config.db_password = db_password
    config.whatsapp_number = whatsapp_number
    config.ai_provider = ai_provider
    config.gemini_api_key = gemini_api_key
    config.ollama_api_url = ollama_api_url
    config.whatsapp_gateway_url = whatsapp_gateway_url
    config.whatsapp_gateway_token = whatsapp_gateway_token
    config.is_active = is_active
    
    db.commit()
    db.refresh(config)
    
    return RedirectResponse(url="/ventas/chatbot?success=true", status_code=303)

@router.post("/chatbot/test-db")
async def test_chatbot_db(
    db_host: str = Form(...),
    db_name: str = Form(...),
    db_user: str = Form(...),
    db_password: str = Form(...),
    user: models.User = Depends(get_current_user)
):
    if user.role not in [1, 4]:
        return JSONResponse(status_code=403, content={"status": "unauthorized"})
        
    success = chatbot_service.test_db_connection(db_host, db_name, db_user, db_password)
    if success:
        return {"status": "ok"}
    else:
        return {"status": "error"}

@router.get("/chatbot/status")
async def get_whatsapp_status(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in [1, 4]:
        return JSONResponse(status_code=403, content={"status": "unauthorized"})
        
    config = chatbot_service.get_chatbot_config(db)
    gateway_url = config.whatsapp_gateway_url.rstrip("/")
    url = f"{gateway_url}/instance/connectionState/carmal_bot"
    headers = {
        "apikey": "carmal_whatsapp_secure_key_2026"
    }
    try:
        import requests
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            return res.json()
        return {"instance": {"state": "disconnected"}}
    except Exception as e:
        return {"instance": {"state": "error", "message": str(e)}}

@router.get("/chatbot/qr")
async def get_whatsapp_qr(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in [1, 4]:
        return JSONResponse(status_code=403, content={"status": "unauthorized"})
        
    config = chatbot_service.get_chatbot_config(db)
    gateway_url = config.whatsapp_gateway_url.rstrip("/")
    
    # Intentar obtener QR de connect
    connect_url = f"{gateway_url}/instance/connect/carmal_bot"
    headers = {
        "apikey": "carmal_whatsapp_secure_key_2026"
    }
    try:
        import requests
        res = requests.get(connect_url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
            
        # Si no existe o falla, intentar crear/inicializar la instancia
        create_url = f"{gateway_url}/instance/create"
        payload = {
            "instanceName": "carmal_bot",
            "token": "carmal_token_2026",
            "qrcode": True
        }
        res_create = requests.post(create_url, json=payload, headers=headers, timeout=10)
        if res_create.status_code in [200, 201]:
            return res_create.json()
            
        return {"status": "error", "message": f"Fallo al conectar: {res.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

