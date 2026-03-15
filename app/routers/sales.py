from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
import datetime
import json
import os
import redis
from dateutil.relativedelta import relativedelta

from app import models, schemas
from app.database import get_db
from app.external_db import get_external_db
from app.dependencies import get_current_user, get_current_active_user, templates

router = APIRouter(
    prefix="/sales",
    tags=["sales"]
)

# === FRONTEND VIEWS ===

@router.get("/", response_class=HTMLResponse)
async def sales_dashboard(
    request: Request,
    current_user: models.User = Depends(get_current_active_user)
):
    return templates.TemplateResponse("sales/dashboard.html", {
        "request": request,
        "user": current_user
    })

@router.get("/forecast", response_class=HTMLResponse)
async def forecast_view(
    request: Request,
    current_user: models.User = Depends(get_current_active_user)
):
    # Only allow certain roles (e.g. Sales, Admin)
    # 1=KPI, 2=Prod, 3=Plan, 4=Admin, 5=Almacen, 6=Inventory, 7=Patrimonial, 8=Director
    if current_user.role not in [1, 4, 8]:
        pass # allow view only, UI logic handles disabling edits
        
    # Determine next month by default
    today = datetime.date.today()
    next_month = today + relativedelta(months=1)
    
    return templates.TemplateResponse("sales/forecast.html", {
        "request": request,
        "user": current_user,
        "default_month": next_month.month,
        "default_year": next_month.year
    })

# === APIs ===

@router.get("/api/forecast/generate")
async def generate_forecast(
    month: int,
    year: int,
    refresh: bool = False,
    db: Session = Depends(get_db),
    external_db: Session = Depends(get_external_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Generates a sales forecast for the given month/year based on a 3-month moving average
    of invoices and delivery notes from Profit Plus.
    Utilizes Redis for high-speed in-memory caching.
    """
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    cache_key = f"forecast_{year}_{month}"
    
    # Attempt to fetch from Redis Cache
    if not refresh:
        try:
            r = redis.Redis.from_url(redis_url, decode_responses=True)
            cached_data = r.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            print(f"Redis connection warning (Cache Miss fallback): {e}")
            r = None
    else:
        try:
            r = redis.Redis.from_url(redis_url, decode_responses=True)
        except Exception:
            r = None
    # 1. Determine the 3-month lookback period
    target_date = datetime.date(year, month, 1)
    start_date = target_date - relativedelta(months=3)
    end_date = target_date - relativedelta(days=1) # Last day of previous month
    
    start_str = start_date.strftime('%Y-%m-%d 00:00:00')
    end_str = end_date.strftime('%Y-%m-%d 23:59:59')
    
    try:
        # Query 1: Facturas (saFacturaVenta)
        sql_fact = text("""
            SELECT 
                r.co_art,
                a.art_des,
                SUM(r.total_art) as qty,
                MAX(ISNULL(u.equivalencia, 1)) as equiv
            FROM saFacturaVenta f
            JOIN saFacturaVentaReng r ON f.doc_num = r.doc_num
            JOIN saArticulo a ON r.co_art = a.co_art
            LEFT JOIN saArtUnidad u ON a.co_art = u.co_art AND u.equivalencia > 1
            WHERE f.fec_emis >= :start_date AND f.fec_emis <= :end_date
              AND f.anulado = 0
            GROUP BY r.co_art, a.art_des
        """)
        
        # Query 2: Notas de Entrega (saNotaEntregaVenta)
        sql_nota = text("""
            SELECT 
                r.co_art,
                a.art_des,
                SUM(r.total_art) as qty,
                MAX(ISNULL(u.equivalencia, 1)) as equiv
            FROM saNotaEntregaVenta f
            JOIN saNotaEntregaVentaReng r ON f.doc_num = r.doc_num
            JOIN saArticulo a ON r.co_art = a.co_art
            LEFT JOIN saArtUnidad u ON a.co_art = u.co_art AND u.equivalencia > 1
            WHERE f.fec_emis >= :start_date AND f.fec_emis <= :end_date
              AND f.anulado = 0
            GROUP BY r.co_art, a.art_des
        """)
        
        res_fact = external_db.execute(sql_fact, {"start_date": start_str, "end_date": end_str}).fetchall()
        res_nota = external_db.execute(sql_nota, {"start_date": start_str, "end_date": end_str}).fetchall()
        
        # Aggregate logic
        aggregated = {}
        def _add_to_agg(rows):
            for r in rows:
                code = r.co_art.strip()
                desc = r.art_des.strip() if r.art_des else "N/A"
                equiv = float(r.equiv) if getattr(r, 'equiv', None) and float(r.equiv) > 0 else 1.0
                if code not in aggregated:
                    aggregated[code] = {"name": desc, "qty_3m": 0.0, "equiv": equiv}
                aggregated[code]["qty_3m"] += float(r.qty or 0.0)
                
        _add_to_agg(res_fact)
        _add_to_agg(res_nota)
        
        # Build Response & Merge with currently saved adjustments (if any)
        # Fetch existing overrides
        existing_overrides = db.query(models.SalesForecast).filter(
            models.SalesForecast.month == month,
            models.SalesForecast.year == year
        ).all()
        override_map = {o.co_art.strip(): o for o in existing_overrides}
        
        final_list = []
        for code, data in aggregated.items():
            total_3m = data["qty_3m"]
            equiv = data["equiv"]
            monthly_avg = total_3m / 3.0
            boxes_avg = monthly_avg / equiv if equiv > 1 else monthly_avg
            
            # Look up manual adjustments
            adjusted_qty = round(monthly_avg, 2)
            adjusted_boxes = round(boxes_avg, 2)
            is_adjusted = False
            override = override_map.get(code)
            
            if override:
                adjusted_qty = override.estimated_qty
                adjusted_boxes = round(adjusted_qty / equiv, 2) if equiv > 1 else adjusted_qty
                is_adjusted = override.is_adjusted
            
            final_list.append({
                "co_art": code,
                "article_name": data["name"],
                "total_past_3m": round(total_3m, 2),
                "suggested_qty": round(monthly_avg, 2),
                "suggested_boxes": round(boxes_avg, 2),
                "estimated_qty": adjusted_qty,
                "estimated_boxes": adjusted_boxes,
                "equiv": equiv,
                "is_adjusted": is_adjusted
            })
            
            # Remove from map to check for items that have no history but were inserted manually
            if code in override_map:
                del override_map[code]
                
        # Items that had 0 sales in last 3m but have a manual forecast row
        for code, override in override_map.items():
             # Since it's zero historical sales, we don't have equiv directly easily, default to 1
             final_list.append({
                "co_art": code,
                "article_name": override.article_name or "Desconocido",
                "total_past_3m": 0.0,
                "suggested_qty": 0.0,
                "suggested_boxes": 0.0,
                "estimated_qty": override.estimated_qty,
                "estimated_boxes": override.estimated_qty,
                "equiv": 1.0,
                "is_adjusted": override.is_adjusted
            })
            
        final_list.sort(key=lambda x: x['article_name'])
        
        payload = {
            "period": f"{month}/{year}",
            "start_history": start_date.strftime("%Y-%m-%d"),
            "end_history": end_date.strftime("%Y-%m-%d"),
            "data": final_list
        }
        
        # Save to Redis Cache with TTL of 1 hour (3600 seconds)
        try:
            if r:
                r.setex(cache_key, 3600, json.dumps(payload))
        except Exception as e:
             print(f"Redis write warning: {e}")
             
        return payload
        
    except Exception as e:
        print(f"Error computing forecast: {e}")
        raise HTTPException(status_code=500, detail="Error de DB externa.")

from pydantic import BaseModel
class ForecastUpdateRow(BaseModel):
    co_art: str
    article_name: str
    suggested_qty: float
    estimated_qty: float
    equiv: float = 1.0

class ForecastUpdateRequest(BaseModel):
    month: int
    year: int
    rows: List[ForecastUpdateRow]

@router.post("/api/forecast/save")
async def save_forecast(
    req: ForecastUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if current_user.role not in [1, 4, 8]: # Admin/Director
        raise HTTPException(status_code=403, detail="Sin permisos para modificar el forecast.")
        
    try:
        for r in req.rows:
            # Check if exists
            existing = db.query(models.SalesForecast).filter(
                models.SalesForecast.month == req.month,
                models.SalesForecast.year == req.year,
                models.SalesForecast.co_art == r.co_art
            ).first()
            
            is_adjusted_flag = (r.estimated_qty != r.suggested_qty)
            
            if existing:
                existing.estimated_qty = r.estimated_qty
                existing.suggested_qty = r.suggested_qty
                existing.is_adjusted = is_adjusted_flag
            else:
                new_row = models.SalesForecast(
                    month=req.month,
                    year=req.year,
                    co_art=r.co_art,
                    article_name=r.article_name,
                    suggested_qty=r.suggested_qty,
                    estimated_qty=r.estimated_qty,
                    is_adjusted=is_adjusted_flag
                )
                db.add(new_row)
        
        db.commit()
        return {"status": "success", "message": "Proyección guardada correctamente."}
        
    except Exception as e:
        db.rollback()
        print(f"Error saving forecast: {e}")
        raise HTTPException(status_code=500, detail="No se pudo guardar la proyección.")

@router.get("/api/mrp/calculate")
async def calculate_forecast_mrp(
    month: int,
    year: int,
    db: Session = Depends(get_db),
    external_db: Session = Depends(get_external_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Calculates Material Requirements Planning (MRP) based on the SAVED forecast for a given month.
    Explodes Bill of Materials (BOM) and balances against current global stock.
    """
    if current_user.role not in [1, 4, 8]: # Admin/Director/KPI
        raise HTTPException(status_code=403, detail="Sin permisos para consultar MRP.")

    try:
        # 1. Fetch saved forecast
        saved_forecast = db.query(models.SalesForecast).filter(
            models.SalesForecast.month == month,
            models.SalesForecast.year == year
        ).all()
        
        if not saved_forecast:
            return {"status": "error", "message": "No hay proyección guardada para este mes."}

        # Format forecast for SQL Injection (Safe parameterized CTE)
        # Using a Values clause strategy or repeated SELECTs for the CTE
        forecast_cte_parts = []
        params = {}
        for i, f in enumerate(saved_forecast):
            if float(f.estimated_qty) > 0:
                p_code = f"code_{i}"
                p_qty = f"qty_{i}"
                forecast_cte_parts.append(f"SELECT :{p_code} as co_art, CAST(:{p_qty} AS DECIMAL(18,2)) as forecast_qty")
                params[p_code] = f.co_art.strip()
                params[p_qty] = float(f.estimated_qty)
        
        if not forecast_cte_parts:
            return {"status": "success", "data": []}
            
        forecast_cte = " UNION ALL ".join(forecast_cte_parts)
        
        dialect = external_db.bind.dialect.name
        
        # 2. Build and execute Explosion Query
        mrp_sql = text(f"""
        WITH Forecast AS (
            {forecast_cte}
        ),
        BOM AS (
            SELECT 
                RTRIM(h.co_art) as p_terminado,
                RTRIM(d.co_art) as componente,
                d.total_art as qty_per_unit
            FROM saArtCompuesto h
            JOIN saArtCompuestoReng d ON h.co_artc = d.co_artc
        ),
        Explosion AS (
            SELECT 
                b.componente,
                a.art_des as descrip,
                a.tipo as tipo_art,
                RTRIM(a.uni_venta) as unidad,
                SUM(f.forecast_qty * b.qty_per_unit) as required_qty
            FROM Forecast f
            JOIN BOM b ON f.co_art = b.p_terminado
            JOIN saArticulo a ON b.componente = a.co_art
            GROUP BY b.componente, a.art_des, a.tipo, a.uni_venta
        ),
        Inventario AS (
            SELECT 
                RTRIM(co_art) as co_art,
                SUM(stock) as stock_actual
            FROM saStockAlmacen
            GROUP BY RTRIM(co_art)
        )
        SELECT 
            e.componente,
            e.descrip,
            e.tipo_art,
            e.unidad,
            e.required_qty,
            ISNULL(i.stock_actual, 0) as stock_actual,
            ISNULL(i.stock_actual, 0) - e.required_qty as deficit
        FROM Explosion e
        LEFT JOIN Inventario i ON e.componente = i.co_art
        ORDER BY deficit ASC
        """)
        
        results = external_db.execute(mrp_sql, params).fetchall()
        
        mrp_data = []
        for r in results:
            mrp_data.append({
                "componente": r.componente.strip(),
                "descrip": r.descrip.strip() if r.descrip else "S/D",
                "tipo_art": r.tipo_art.strip() if r.tipo_art else "",
                "unidad": r.unidad.strip() if r.unidad else "",
                "required_qty": float(r.required_qty),
                "stock_actual": float(r.stock_actual),
                "deficit": float(r.deficit)
            })
            
        return {"status": "success", "data": mrp_data}

    except Exception as e:
        print(f"Error computing MRP: {e}")
        raise HTTPException(status_code=500, detail="Error de cálculo de MRP.")

