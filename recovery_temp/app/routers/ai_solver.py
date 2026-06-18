
from fastapi import APIRouter, Depends, HTTPException
from app.services.stock_solver import StockSolver
from app import models
from app.dependencies import get_current_active_user

router = APIRouter(
    prefix="/api/ai/stock",
    tags=["ai-stock"],
    responses={404: {"description": "Not found"}},
)

@router.get("/diagnose")
async def diagnose_stock_issues(user: models.User = Depends(get_current_active_user)):
    """
    Scans for stock issues using the StockSolver services.
    """
    return StockSolver.get_diagnostics()

@router.post("/fix")
async def fix_stock_issue(payload: dict, user: models.User = Depends(get_current_active_user)):
    """
    Fixes a specific issue. Payload: { "issue_id": "GUID", "type": "ISSUE_TYPE" }
    """
    issue_id = payload.get("id")
    issue_type = payload.get("type")
    
    if not issue_id or not issue_type:
        raise HTTPException(status_code=400, detail="Missing id or type")
        
    result = StockSolver.fix_issue(issue_id, issue_type)
    
    if not result.get("success"):
         raise HTTPException(status_code=400, detail=result.get("message"))
         
    return result
