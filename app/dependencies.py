from fastapi import Request, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import User

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Auth Dependency ---
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    user = db.query(User).filter(User.id == int(user_id)).first()
    return user

async def get_current_active_user(user: User = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not Authenticated")
    return user

# --- Templates ---
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="app/templates")
