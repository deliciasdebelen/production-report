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
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="app/templates")

# --- RBAC Permissions ---
import json
from fastapi import HTTPException

def check_permission(user: User, module: str, action: str) -> bool:
    """
    Checks if user has permission for a specific module and action.
    Admin (Role 4) always has access.
    """
    if user.role == 4: return True
    
    if not user.role_obj:
        return False
        
    try:
        perms = json.loads(user.role_obj.permissions)
    except:
        return False
        
    # Check Module
    if "all" in perms: return True
    if module not in perms: return False
    
    actions = perms[module]
    if "*" in actions: return True
    if action in actions: return True
    
    return False

# Register for usage in Templates
templates.env.globals['check_permission'] = check_permission

def has_permission(module: str, action: str):
    def dependency(user: User = Depends(get_current_active_user)):
        if not check_permission(user, module, action):
            raise HTTPException(status_code=403, detail="Permiso Denegado")
        return user
    return dependency
