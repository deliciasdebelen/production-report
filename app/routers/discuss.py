from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, aliased
from sqlalchemy import desc, func, and_
from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_active_user
from datetime import datetime

router = APIRouter(
    prefix="/discuss",
    tags=["discuss"]
)

templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def view_discuss(request: Request, user: models.User = Depends(get_current_active_user)):
    return templates.TemplateResponse("discuss.html", {"request": request, "title": "Conversaciones", "user": user})

# --- Helper ---
def format_message(m, status=None):
    author_name = m.author.username if m.author else "Sistema"
    is_starred = status.is_starred if status else False
    is_read = status.is_read if status else False
    return {
        "id": m.id,
        "body": m.body,
        "author": author_name,
        "date": m.created_at.strftime("%H:%M") if m.created_at.date() == datetime.today().date() else m.created_at.strftime("%d/%m"),
        "full_date": m.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "type": m.message_type,
        "channel": m.channel.name if m.channel else "General",
        "is_starred": is_starred,
        "is_read": is_read
    }

# --- API Endpoints ---

@router.get("/api/messages/inbox")
def get_inbox_messages(db: Session = Depends(get_db), user: models.User = Depends(get_current_active_user)):
    # Inbox = Messages where user status is NOT read OR user has no status (for broadcast) but we need to create status first?
    # For simplicity: We query messages and LEFT JOIN status. 
    # If status is NULL -> it's unread. If status.is_read is False -> Unread.
    
    # Actually, proper Odoo logic creates Mail.notification for each recipient.
    # Simplified Logic:
    # 1. Fetch recent messages from subscribed channels (assume "General" + "Admin" if role=4)
    # 2. Filter out those explicitly marked as read.
    
    Status = aliased(models.MessageStatus)
    
    # Subquery or simple list of channel IDs? 
    # Assuming user sees all Public channels for now.
    
    msgs = db.query(models.Message, Status)\
        .outerjoin(Status, and_(Status.message_id == models.Message.id, Status.user_id == user.id))\
        .filter(models.Message.channel_id != None)\
        .order_by(desc(models.Message.created_at))\
        .limit(50).all()
        
    data = []
    for m, s in msgs:
        # If marked read, skip (it goes to history)
        if s and s.is_read:
            continue
        # Else, show in Inbox
        data.append(format_message(m, s))
        
    return data

@router.get("/api/messages/starred")
def get_starred_messages(db: Session = Depends(get_db), user: models.User = Depends(get_current_active_user)):
    Status = aliased(models.MessageStatus)
    results = db.query(models.Message, Status)\
        .join(Status, and_(Status.message_id == models.Message.id, Status.user_id == user.id))\
        .filter(Status.is_starred == True)\
        .order_by(desc(models.Message.created_at))\
        .all()
        
    return [format_message(m, s) for m, s in results]

@router.get("/api/messages/history")
def get_history_messages(db: Session = Depends(get_db), user: models.User = Depends(get_current_active_user)):
    # History = Messages marked Read
    Status = aliased(models.MessageStatus)
    results = db.query(models.Message, Status)\
        .join(Status, and_(Status.message_id == models.Message.id, Status.user_id == user.id))\
        .filter(Status.is_read == True)\
        .order_by(desc(models.Message.created_at))\
        .limit(50).all()
        
    return [format_message(m, s) for m, s in results]

@router.post("/api/message/{id}/mark_read")
def mark_read(id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_active_user)):
    status = db.query(models.MessageStatus).filter_by(message_id=id, user_id=user.id).first()
    if not status:
        status = models.MessageStatus(message_id=id, user_id=user.id)
        db.add(status)
    
    status.is_read = True
    db.commit()
    return {"status": "ok"}

@router.post("/api/message/{id}/star")
def toggle_star(id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_active_user)):
    status = db.query(models.MessageStatus).filter_by(message_id=id, user_id=user.id).first()
    if not status:
        status = models.MessageStatus(message_id=id, user_id=user.id)
        db.add(status)
    
    status.is_starred = not status.is_starred
    db.commit()
    return {"status": "ok", "starred": status.is_starred}

@router.post("/api/message")
def post_message(
    body: str = Form(...), 
    channel_id: int = Form(...),
    db: Session = Depends(get_db), 
    user: models.User = Depends(get_current_active_user)
):
    msg = models.Message(
        body=body,
        author_id=user.id,
        channel_id=channel_id,
        message_type='comment'
    )
    db.add(msg)
    db.commit() # commit to get ID
    
    # Optionally mark as read for sender?
    status = models.MessageStatus(message_id=msg.id, user_id=user.id, is_read=True)
    db.add(status)
    db.commit()
    
    db.refresh(msg)
    return {"status": "ok", "id": msg.id}

@router.get("/api/channels")
def get_channels(db: Session = Depends(get_db), user: models.User = Depends(get_current_active_user)):
    channels = db.query(models.Channel).filter(models.Channel.type == 'channel').all()
    return [{"id": c.id, "name": c.name, "type": c.type} for c in channels]

@router.post("/api/init_channels")
def init_channels(db: Session = Depends(get_db)):
    if not db.query(models.Channel).first():
        db.add(models.Channel(name="General", type="channel"))
        db.add(models.Channel(name="Administrators", type="channel"))
        db.commit()
        return {"status": "seeded"}
    return {"status": "already_exists"}

@router.get("/api/messages/recent")
def get_recent_preview(limit: int = 10, db: Session = Depends(get_db), user: models.User = Depends(get_current_active_user)):
    # Dropdown logic: Show Inbox items first?
    # Reusing logic similar to Inbox but simplified
    msgs = db.query(models.Message).order_by(desc(models.Message.created_at)).limit(limit).all()
    data = []
    for m in msgs:
         data.append(format_message(m)) # Basic format without status check for preview
    return data
