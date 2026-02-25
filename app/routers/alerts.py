from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from .. import models, schemas, auth_utils
from app.database import get_db
from app.dependencies import get_current_active_user, templates
import os
import json

router = APIRouter(
    prefix="/alerts",
    tags=["alerts"]
)

DOCS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'docs')
JSON_PATH = os.path.join(DOCS_DIR, 'latest_results.json')

@router.get("/", response_class=HTMLResponse)
async def view_alerts(request: Request, user: models.User = Depends(get_current_active_user)):
    return templates.TemplateResponse("alerts.html", {"request": request, "title": "Alertas y Auditoría", "user": user})

@router.get("/api/data")
async def get_alerts_data(user: models.User = Depends(get_current_active_user)):
    if not os.path.exists(JSON_PATH):
        return {"status": "no_data", "timestamp": None, "audit": [], "purchasing": []}
    
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {
                "status": "ok", 
                "timestamp": data.get("timestamp"),
                "audit": data.get("audit_data", []),
                "purchasing": data.get("purchasing_data", []),
                "summary": data.get("summary", "")
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}
