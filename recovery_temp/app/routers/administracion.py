from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from app.dependencies import get_current_user, templates
from app import models

router = APIRouter(
    prefix="/administracion",
    tags=["administracion"]
)

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def view_admin_dashboard(request: Request, user: models.User = Depends(get_current_user)):
    return templates.TemplateResponse("administracion/index.html", {
        "request": request,
        "title": "Administración",
        "user": user
    })
