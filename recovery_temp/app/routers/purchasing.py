from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any

from app import models, schemas
from app.database import get_db
from app.dependencies import get_current_user, get_current_active_user, templates

router = APIRouter(
    prefix="/purchasing",
    tags=["Purchasing", "MRP"],
    responses={404: {"description": "Not found"}},
)

@router.get("/mrp", response_class=templates.TemplateResponse)
async def mrp_dashboard(
    request: Request,
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Render MRP Dashboard for Purchasing.
    """
    return templates.TemplateResponse(
        "compras/mrp.html",
        {
            "request": request,
            "title": "Alertas MRP (Abastecimiento)",
            "user": current_user,
        }
    )

@router.get("/api/mrp/alerts")
def get_mrp_alerts(
    month: int,
    year: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Calculate Raw Material Shortages based on Sales Forecasts for the specified month/year.
    This explores the BOM (Bill of Materials) in the local replica tables (profit_formula)
    and crosses it with the current local replica inventory (profit_stock_almacen).
    """
    try:
        # 1. Fetch Sales Forecasts for the target month/year
        forecasts = db.query(models.SalesForecast).filter(
            models.SalesForecast.month == month,
            models.SalesForecast.year == year
        ).all()
        
        if not forecasts:
            return {"data": [], "message": "No hay proyecciones de ventas cargadas para este mes."}
            
        # We will aggregate gross demand per raw material SKU
        raw_material_demand = {} # co_art -> {art_des: str, qty: float, co_uni: str}
        
        for f in forecasts:
            est_qty = f.estimated_qty
            if est_qty <= 0:
                continue
            
            co_art_pt = f.co_art.strip()
            
            # Find default formula for this finish good in local replica
            form_res = db.query(models.ProfitFormula).filter(
                models.ProfitFormula.co_art == co_art_pt,
                models.ProfitFormula.fpredeterminada == True
            ).first()
            
            if not form_res:
                continue
                
            co_for = form_res.co_for
            
            # Get ingredients for this formula in local replica
            ing_res = db.query(models.ProfitFormulaReng).filter(
                models.ProfitFormulaReng.co_for == co_for
            ).all()
            
            for ing in ing_res:
                ing_art = ing.co_art.strip()
                unit_qty = ing.cantidad or 0.0
                uom = ing.co_uni.strip() if ing.co_uni else 'UND'
                
                total_req = est_qty * unit_qty
                
                if ing_art not in raw_material_demand:
                    raw_material_demand[ing_art] = {"qty": 0.0, "co_uni": uom}
                
                raw_material_demand[ing_art]["qty"] += total_req
                
        # 2. Cross reference with Inventory AND Details
        alerts = []
        
        for ing_art, demand in raw_material_demand.items():
            # Skip if N/A or empty
            if ing_art == 'N/A' or not ing_art:
                continue
                
            # Query local replica for stock and description
            art_res = db.query(models.ProfitArticulo).filter(models.ProfitArticulo.co_art == ing_art).first()
            art_des = art_res.art_des.strip() if art_res and art_res.art_des else "Desconocido"
            
            stock_res = db.query(models.ProfitStockAlmacen).filter(
                models.ProfitStockAlmacen.co_art == ing_art,
                models.ProfitStockAlmacen.co_alma.in_(['ALM01', 'ALM02'])
            ).all()
            
            current_stock = sum(s.stock for s in stock_res)
            
            demand_qty = demand["qty"]
            shortage = max(0, demand_qty - current_stock)
            
            status = "green"
            if shortage > 0:
                status = "red"
            elif current_stock < demand_qty * 1.2: # 20% safety margin warning
                status = "yellow"
                
            alerts.append({
                "co_art": ing_art,
                "art_des": art_des,
                "demand": round(demand_qty, 2),
                "stock": round(current_stock, 2),
                "shortage": round(shortage, 2),
                "uom": demand["co_uni"],
                "status": status
            })
            
        # Sort by shortage descending
        alerts.sort(key=lambda x: x["shortage"], reverse=True)
        
        return {"data": alerts, "message": "Cálculo MRP completado extiosamente."}
        
    except Exception as e:
        print(f"MRP Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/mrp/sync")
def trigger_mrp_sync(current_user: models.User = Depends(get_current_active_user)):
    """
    On-demand manual trigger to run the ETL sync script from Profit Plus to local Postgres.
    """
    if current_user.role not in [1, 3]: # Only Admin or Managers
        raise HTTPException(status_code=403, detail="No autorizado para forzar sincronización.")
        
    try:
        import sync_profit_replica
        sync_profit_replica.sync_profit_data()
        return {"status": "ok", "message": "Fórmulas y Catálogos sincronizados desde Profit Plus exitosamente."}
    except Exception as e:
        print(f"Sync Error: {e}")
        raise HTTPException(status_code=500, detail="Error interno durante la sincronización.")
