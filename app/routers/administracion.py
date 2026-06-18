from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from app.dependencies import get_current_user
from app import models

router = APIRouter(
    prefix="/administracion",
    tags=["administracion"]
)

@router.get("")
@router.get("/")
async def view_admin_dashboard(request: Request, user: models.User = Depends(get_current_user)):
    return RedirectResponse(url="/sistema")
