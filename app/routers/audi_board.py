from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Role, AudiLog
from app.dependencies import get_current_active_user, templates

router = APIRouter()

@router.get("/audi", response_class=HTMLResponse)
async def view_audi_board(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    # Restrict to Admin, Finance, Directors
    if current_user.role not in [1, 4, 8]:
        raise HTTPException(status_code=403, detail="No tiene permisos para ver auditorías de IA")
    
    # Fetch logs, order by date descending
    logs = db.query(AudiLog).order_by(AudiLog.created_at.desc()).all()
    
    # Pre-parse Markdown syntax (or simple newlines) to HTML for safe display
    for log in logs:
        # Markdown parsing might fail if markdown library is not installed, so wrapping it
        try:
            import markdown
            log.html_content = markdown.markdown(log.report_text)
        except:
            log.html_content = log.report_text.replace("\n", "<br>")

    return templates.TemplateResponse("audi_board.html", {
        "request": request, 
        "title": "Auditoría IA (Audi)", 
        "user": current_user,
        "logs": logs
    })
