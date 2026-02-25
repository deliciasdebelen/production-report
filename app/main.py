from fastapi import FastAPI, Request, Depends, HTTPException, Form, Response, Cookie, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import shutil
import os
from fastapi.staticfiles import StaticFiles
import json
from sqlalchemy.orm import Session
from . import models, schemas, auth_utils
from app.database import engine, Base, get_db, SessionLocal
from app.external_db import get_external_db, external_engine
from sqlalchemy import text


from .routers import external, traslados
from typing import Optional
import datetime
import random

COLORS = [
    "#ef4444", "#f97316", "#f59e0b", "#84cc16", "#10b981", 
    "#06b6d4", "#3b82f6", "#6366f1", "#8b5cf6", "#d946ef", 
    "#f43f5e", "#0ea5e9"
]

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Reporte de Produccion")

from .routers import external, traslados, visor, inventory, logistics, reports, maintenance, discuss

app.include_router(external.router)
app.include_router(traslados.router)
app.include_router(visor.router)
app.include_router(inventory.router)
app.include_router(logistics.router)
app.include_router(reports.router)
app.include_router(maintenance.router)
app.include_router(discuss.router)

from .routers import support
app.include_router(support.router)

from .routers import export
app.include_router(export.router)

from .routers import ai_solver
from .routers import ai_solver
app.include_router(ai_solver.router)

from .routers import assistant
app.include_router(assistant.router)

from .routers import semaforo
app.include_router(semaforo.router)

from .routers import semaforo2
app.include_router(semaforo2.router)

from .routers import compras_mp
app.include_router(compras_mp.router)

from .routers import telegram_admin
app.include_router(telegram_admin.router)

from app.utils_id import get_next_order_number

@app.get("/api/next-id/{model_name}")
def get_next_id(model_name: str, db: Session = Depends(get_db)):
    model = None
    if model_name == "planning": model = models.ProductionPlanning
    elif model_name == "production": model = models.ProductionReport
    
    if model:
        return {"next_id": get_next_order_number(db, model)}
    return {"next_id": 1}

@app.get("/api/debug/db-connection")
def debug_db_connection():
    try:
        with external_engine.connect() as conn:
            result = conn.execute(text("SELECT @@VERSION")).fetchone()
            return {"status": "ok", "version": result[0]}
    except Exception as e:
        return {"status": "error", "details": str(e)}

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Dependencies moved to dependencies.py
from .dependencies import get_db, get_current_user, get_current_active_user, templates

@app.on_event("startup")
def startup_db_client():
    # Create default admin if not exists
    db = SessionLocal()
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin:
        hashed = auth_utils.get_password_hash("admin")
        admin = models.User(username="admin", password_hash=hashed, role=4)
        db.add(admin)
        db.commit()
    db.close()

# --- Views ---

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(response: Response, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return RedirectResponse(url="/login?error=invalid_user", status_code=303)
    if not auth_utils.verify_password(password, user.password_hash):
        return RedirectResponse(url="/login?error=invalid_password", status_code=303)
    
    # Simple Cookie Session (In prod, use signed tokens)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="user_id", value=str(user.id))
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("user_id")
    return response

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, user: models.User = Depends(get_current_user)):
    if not user: return RedirectResponse("/login")
    return templates.TemplateResponse("index.html", {"request": request, "title": "Home", "user": user})

@app.get("/report", response_class=HTMLResponse)
async def view_report(request: Request, user: models.User = Depends(get_current_active_user)):
    if user.role not in [2, 4]: # 2=Prod, 4=Admin
        return templates.TemplateResponse("403.html", {"request": request, "user": user})
    return templates.TemplateResponse("report.html", {"request": request, "title": "Reporte", "user": user})

@app.get("/planning", response_class=HTMLResponse)
async def view_planning(request: Request, user: models.User = Depends(get_current_active_user)):
    if user.role not in [3, 4]:
        return templates.TemplateResponse("403.html", {"request": request, "user": user})
    return templates.TemplateResponse("planning.html", {"request": request, "title": "Orden de Planificación", "user": user})

@app.get("/api/planning/pending")
def get_pending_planning(db: Session = Depends(get_db)):
    # Return formatted list for dropdown
    plans = db.query(models.ProductionPlanning).filter(
        models.ProductionPlanning.status == 'Pending'
    ).order_by(models.ProductionPlanning.id.asc()).all()
    
    return [{
        "id": p.id,
        "label": f"#{p.order_number or p.id} - {p.article}",
        "article": p.article,
        "presentation": p.presentation,
        "units": p.units_pending if p.units_pending is not None else p.units, # Return REMAINING
        "total_units": p.units,
        "waste_percentage": p.waste_percentage,
        "kg": p.kg,
        "batches": p.batches
    } for p in plans]

@app.get("/dashboard", response_class=HTMLResponse)
async def view_dashboard(request: Request, user: models.User = Depends(get_current_active_user)):
    return templates.TemplateResponse("dashboard.html", {"request": request, "title": "Dashboard", "user": user})

@app.get("/visor", response_class=HTMLResponse)
async def view_visor(request: Request, user: models.User = Depends(get_current_active_user)):
    return templates.TemplateResponse("visor.html", {"request": request, "title": "Visor de Producción", "user": user})

@app.get("/assistant", response_class=HTMLResponse)
async def view_assistant(request: Request, user: models.User = Depends(get_current_active_user)):
     return templates.TemplateResponse("assistant.html", {"request": request, "title": "Asistente", "user": user})

# @app.get("/maintenance", response_class=HTMLResponse)
# async def view_maintenance(request: Request, db: Session = Depends(get_db), user: models.User = Depends(get_current_active_user)):
#     if user.role != 4:
#         return templates.TemplateResponse("403.html", {"request": request, "user": user})
#     
#     users = db.query(models.User).all()
#     return templates.TemplateResponse("maintenance.html", {"request": request, "title": "Mantenimiento", "user": user, "users": users})


# --- Support Pages ---

@app.get("/support", response_class=HTMLResponse)
async def view_support_index(request: Request, user: models.User = Depends(get_current_active_user)):
    return templates.TemplateResponse("support/index.html", {"request": request, "title": "Soporte", "current_user": user, "user": user})

@app.get("/support/create", response_class=HTMLResponse)
async def view_support_create(request: Request, user: models.User = Depends(get_current_active_user)):
    return templates.TemplateResponse("support/create_ticket.html", {"request": request, "title": "Crear Ticket", "current_user": user, "user": user})

@app.get("/support/tickets", response_class=HTMLResponse)
async def view_support_list(request: Request, user: models.User = Depends(get_current_active_user)):
    # Everyone can view tickets? Or just their own? The template handles logic. Admin sees all.
    return templates.TemplateResponse("support/management.html", {"request": request, "title": "Gestión de Tickets", "current_user": user, "user": user})

@app.get("/support/config", response_class=HTMLResponse)
async def view_support_config(request: Request, user: models.User = Depends(get_current_active_user)):
    if user.role != 4:
         raise HTTPException(status_code=403, detail="Access denied")
    return templates.TemplateResponse("support/config.html", {"request": request, "title": "Configuración Soporte", "current_user": user, "user": user})



# --- API Endpoints (Protected? Maybe allow allow all auth users for now) ---
from .utils import generate_next_order_number

# ... (imports)

@app.post("/api/production", response_model=schemas.ProductionReport)
async def create_production_report(
    batch_qty: int = Form(...),
    article_type: str = Form(...),
    kg_produced: float = Form(...),
    presentation: str = Form(...),
    boxes: float = Form(0.0),
    pt_units: int = Form(0),
    pt_lab: int = Form(0),
    pt_burned: int = Form(0),
    mp_containers: int = Form(0),
    mp_caps_clean: int = Form(0),
    mp_caps_dirty: int = Form(0),
    mp_waste_kg: float = Form(0.0),
    mp_waste_image: Optional[UploadFile] = File(None),
    cons_type: Optional[str] = Form(None),
    cons_count: float = Form(0.0),
    cons_unit_weight: float = Form(0.0),
    cons_qty: float = Form(0.0),
    notes: Optional[str] = Form(None),
    custom_created_at: Optional[str] = Form(None),
    planning_order_id: int = Form(...), # Mandatory linkage
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Role Check: Production (2) or Admin (4)
    if current_user.role not in [2, 4]:
        raise HTTPException(status_code=403, detail="No tiene permisos para crear reportes de producción")

    try:
        # --- VALIDATION LOGIC ---
        planning_order = db.query(models.ProductionPlanning).filter(models.ProductionPlanning.id == planning_order_id).first()
        if not planning_order:
            raise HTTPException(status_code=400, detail="Orden de Planificación inválida")

        # Validation with Partial Consumption
        # Initialize units_pending if None (Legacy safety)
        if planning_order.units_pending is None:
            planning_order.units_pending = planning_order.units

        if pt_units > planning_order.units_pending:
             raise HTTPException(status_code=400, detail=f"Exceso: {pt_units} supera el pendiente ({planning_order.units_pending}).")

        # Deduct
        planning_order.units_pending -= pt_units

        # Update Status
        if planning_order.units_pending <= 0:
            planning_order.status = "Processed"
            planning_order.units_pending = 0 # Safety
        else:
            planning_order.status = "Pending" # Keeps open

        # --- END VALIDATION ---
        
        # Handle File Upload
        image_path = None
        try:
            if mp_waste_image and mp_waste_image.filename:
                upload_dir = "app/static/uploads/waste"
                os.makedirs(upload_dir, exist_ok=True)
                ext = os.path.splitext(mp_waste_image.filename)[1]
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                safe_name = f"waste_{timestamp}{ext}"
                file_location = f"{upload_dir}/{safe_name}"
                with open(file_location, "wb") as buffer:
                    shutil.copyfileobj(mp_waste_image.file, buffer)
                image_path = f"/static/uploads/waste/{safe_name}"
        except Exception as e:
            print(f"UPLOAD ERROR: {e}")

        # Handle Date Override
        created_at_val = None
        if custom_created_at and current_user.role == 4:
            try:
                 d = datetime.datetime.strptime(custom_created_at, "%Y-%m-%d")
                 # Fixed logic:
                 created_at_val = datetime.datetime.combine(d.date(), datetime.time.min)
            except Exception as e:
                 print(f"DATE ERROR: {e}")

        # Generate Order Number
        print("Generating order number...")
        order_number = generate_next_order_number(db, models.ProductionReport)
        print(f"Order number generated: {order_number}")

        db_report = models.ProductionReport(
            batch_qty=batch_qty,
            article_type=article_type,
            kg_produced=kg_produced,
            presentation=presentation,
            boxes=boxes,
            pt_units=pt_units,
            pt_lab=pt_lab,
            pt_burned=pt_burned,
            mp_containers=mp_containers,
            mp_caps_clean=mp_caps_clean,
            mp_caps_dirty=mp_caps_dirty,
            mp_waste_kg=mp_waste_kg,
            mp_waste_image=image_path,
            cons_type=cons_type,
            cons_count=cons_count,
            cons_unit_weight=cons_unit_weight,
            cons_qty=cons_qty,
            notes=notes,
            order_number=order_number,
            planning_order_ids=str(planning_order_id), # Save the link
            color=planning_order.color # Propagate Color
        )
        
        if created_at_val:
            db_report.created_at = created_at_val

        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        
        return db_report
    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

@app.put("/api/production/{report_id}", response_model=schemas.ProductionReport)
def update_production_report(report_id: str, report: schemas.ProductionReportCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    # Role Check: Production (2) or Admin (4)
    if current_user.role not in [2, 4]:
        raise HTTPException(status_code=403, detail="No tiene permisos para modificar reportes de producción")

    db_report = db.query(models.ProductionReport).filter(models.ProductionReport.id == report_id).first()
    if not db_report:
        raise HTTPException(404, "Reporte no encontrado")
    
    # Update fields
    data = report.dict(exclude_unset=True)
    
    # Handle custom date override logic for admins
    if 'custom_created_at' in data:
         d = data.pop('custom_created_at')
         if d:
            db_report.created_at = datetime.datetime.combine(d, datetime.time.min)
    
    for k, v in data.items():
         # Skip fields not in model or special handling
         if hasattr(db_report, k):
             setattr(db_report, k, v)
    
    db.commit()
    db.refresh(db_report)
    return db_report

@app.post("/api/production/link-planning")
def link_planning_to_production(planning_id: int = Form(...), production_id: str = Form(...), db: Session = Depends(get_db)):
    plan = db.query(models.ProductionPlanning).filter(models.ProductionPlanning.id == planning_id).first()
    if plan:
        plan.status = "Processed"
        db.commit()
    return {"status": "ok"}

@app.get("/api/production", response_model=list[schemas.ProductionReport])
def read_production_reports(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    reports = db.query(models.ProductionReport).order_by(models.ProductionReport.created_at.desc()).offset(skip).limit(limit).all()
    return reports

@app.get("/api/production/latest")
def get_latest_production(db: Session = Depends(get_db)):
    report = db.query(models.ProductionReport).order_by(models.ProductionReport.id.desc()).first()
    if not report: raise HTTPException(404, "No found")
    return report

@app.get("/api/production/autosuggest")
def autosuggest_production(query: str, db: Session = Depends(get_db)):
    if not query: return []
    results = db.query(models.ProductionReport.order_number, models.ProductionReport.id)\
        .filter(models.ProductionReport.order_number.like(f"{query}%"))\
        .limit(5).all()
    return [{"id": r.id, "order_number": str(r.order_number).zfill(8)} for r in results]

@app.get("/api/production/search")
def search_production(query: str, db: Session = Depends(get_db)):
    report = db.query(models.ProductionReport).filter(models.ProductionReport.order_number == query).first()
    if not report and query.isdigit():
        q_int = str(int(query)) # Try stripping zeros (if stored as such, or just match logic)
        report = db.query(models.ProductionReport).filter(models.ProductionReport.order_number == q_int).first()
    
    if not report: raise HTTPException(404, "Not found")
    return report

@app.get("/api/production/{id}/navigate")
def navigate_production(id: str, direction: str, db: Session = Depends(get_db)):
    # Validar actual
    current = db.query(models.ProductionReport).filter(models.ProductionReport.id == id).first()
    if not current: raise HTTPException(404, "Reporte actual no encontrado")

    if direction == 'prev':
        rep = db.query(models.ProductionReport).filter(models.ProductionReport.order_number < current.order_number).order_by(models.ProductionReport.order_number.desc()).first()
    elif direction == 'next':
        rep = db.query(models.ProductionReport).filter(models.ProductionReport.order_number > current.order_number).order_by(models.ProductionReport.order_number.asc()).first()
    else: raise HTTPException(400)
    
    if not rep: raise HTTPException(404)
    return rep

# @app.put("/api/production/{id}") # Duplicate removed
# def update_production(id: int, report_in: schemas.ProductionReportCreate, db: Session = Depends(get_db)):
    db_report = db.query(models.ProductionReport).filter(models.ProductionReport.id == id).first()
    if not db_report: raise HTTPException(404)
    
    # Exclude special fields if needed, but schema usually handles it
    data = report_in.dict(exclude_unset=True) 
    # Handle created_at special logic if passed? Usually read-only on update or strict. 
    # For now allow updating all non-primary.
    for k, v in data.items():
        if k != 'order_number': # protect order number?
             setattr(db_report, k, v)
    
    db.commit()
    db.refresh(db_report)
    return db_report

@app.post("/api/planning", response_model=schemas.ProductionPlanning)
def create_planning(plan: schemas.ProductionPlanningCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    # Role Check: Planning (3) or Admin (4)
    if current_user.role not in [3, 4]:
        raise HTTPException(status_code=403, detail="No tiene permisos para crear planificaciones")

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    if plan.date < today_str and current_user.role != 4:
        raise HTTPException(status_code=403, detail="Solo administradores pueden planificar fechas pasadas")

    plan_data = plan.dict()
    plan_data['order_number'] = generate_next_order_number(db, models.ProductionPlanning)
    plan_data['units_pending'] = plan.units # Initialize countdown
    plan_data['color'] = random.choice(COLORS) # Assign Random Color

    db_plan = models.ProductionPlanning(**plan_data)
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan

@app.get("/api/planning", response_model=list[schemas.ProductionPlanning])
def read_planning(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    plans = db.query(models.ProductionPlanning).order_by(models.ProductionPlanning.id.desc()).offset(skip).limit(limit).all()
    return plans

@app.get("/api/planning/by-date/{date_str}")
def get_planning_by_date(date_str: str, db: Session = Depends(get_db)):
    plans = db.query(models.ProductionPlanning).filter(
        models.ProductionPlanning.date == date_str,
        models.ProductionPlanning.status == 'Pending'
    ).all()
    return plans

    db.delete(plan)
    db.commit()
    return {"status": "deleted"}

@app.get("/api/planning/search")
def search_planning(query: str, db: Session = Depends(get_db)):
    # Query is expected to be the order number (e.g. "5" or "00000005")
    # Our DB stores it as generated string or int? 
    # utils_id helper usually makes it an int in DB if column is Integer, but model.order_number is String.
    # Let's try exact match first, then lstrip zeros.
    
    # Try exact
    plan = db.query(models.ProductionPlanning).filter(models.ProductionPlanning.order_number == query).first()
    if plan: return plan
    
    # Try integer version (stripping zeros) if query is digit
    if query.isdigit():
        q_int = str(int(query))
        plan = db.query(models.ProductionPlanning).filter(models.ProductionPlanning.order_number == q_int).first()
        if plan: return plan
        
    raise HTTPException(404, "Documento no encontrado")

@app.get("/api/planning/latest")
def get_latest_planning(db: Session = Depends(get_db)):
    plan = db.query(models.ProductionPlanning).order_by(models.ProductionPlanning.id.desc()).first()
    if not plan:
        raise HTTPException(404, "No records found")
    return plan

@app.get("/api/planning/autosuggest")
def autosuggest_planning(query: str, db: Session = Depends(get_db)):
    if not query: return []
    results = db.query(models.ProductionPlanning.order_number, models.ProductionPlanning.id)\
        .filter(models.ProductionPlanning.order_number.like(f"{query}%"))\
        .limit(5).all()
    return [{"id": r.id, "order_number": r.order_number} for r in results]

@app.get("/api/planning/{id}/navigate")
def navigate_planning(id: int, direction: str, db: Session = Depends(get_db)):
    if direction == 'prev':
        plan = db.query(models.ProductionPlanning).filter(models.ProductionPlanning.id < id).order_by(models.ProductionPlanning.id.desc()).first()
    elif direction == 'next':
        plan = db.query(models.ProductionPlanning).filter(models.ProductionPlanning.id > id).order_by(models.ProductionPlanning.id.asc()).first()
    else:
        raise HTTPException(400, "Invalid direction")
        
    if not plan:
        raise HTTPException(404, "No more records")
        
    return plan

@app.put("/api/planning/{id}", response_model=schemas.ProductionPlanning)
def update_planning(id: int, plan: schemas.ProductionPlanningCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    # Role Check: Planning (3) or Admin (4)
    if current_user.role not in [3, 4]:
        raise HTTPException(status_code=403, detail="No tiene permisos para modificar planificaciones")

    db_plan = db.query(models.ProductionPlanning).filter(models.ProductionPlanning.id == id).first()
    if not db_plan:
        raise HTTPException(404, "Plan no encontrado")
        
    # Update fields
    for key, value in plan.dict().items():
        setattr(db_plan, key, value)
        
    db.commit()
    db.refresh(db_plan)
    return db_plan

@app.get("/api/dashboard", response_model=schemas.DashboardStats)
def get_dashboard_stats(start_date: Optional[str] = None, end_date: Optional[str] = None, db: Session = Depends(get_db)):
    # Simple aggregation
    q_rep = db.query(models.ProductionReport)
    q_plan = db.query(models.ProductionPlanning)

    if start_date:
        try:
            sd = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            q_rep = q_rep.filter(models.ProductionReport.created_at >= sd)
            q_plan = q_plan.filter(models.ProductionPlanning.date >= start_date)
        except ValueError:
            pass # Ignore invalid date format

    if end_date:
        try:
            ed = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            # Include the entire end day
            ed_end = datetime.datetime.combine(ed, datetime.time.max) 
            q_rep = q_rep.filter(models.ProductionReport.created_at <= ed_end)
            q_plan = q_plan.filter(models.ProductionPlanning.date <= end_date)
        except ValueError:
            pass

    reports = q_rep.all()
    plans = q_plan.all()

    total_prod_batches = sum((r.batch_qty or 0) for r in reports)
    # Total Kg = Kg Produced (Batches) + Consumo Rapido (Quick Consumption)
    total_prod_kg = sum(((r.kg_produced or 0) + (r.cons_qty or 0)) for r in reports)
    total_prod_units = sum((r.pt_units or 0) for r in reports)
    total_prod_boxes = sum((r.boxes or 0) for r in reports) 
    total_waste_kg = sum((r.mp_waste_kg or 0) for r in reports)

    total_plan_batches = sum((p.batches or 0) for p in plans)
    total_plan_kg = sum((p.kg or 0) for p in plans)
    total_plan_units = sum((p.units or 0) for p in plans)

    # Compliance
    if total_plan_units > 0:
        compliance = (total_prod_units / total_plan_units) * 100
    else:
        compliance = 0.0

    if total_plan_kg > 0:
        yield_pct = (total_prod_kg / total_plan_kg) * 100
    else:
        yield_pct = 0.0

    # Waste (Burned+Lab / Total Produced Units)
    total_waste_units = sum(((r.pt_burned or 0) + (r.pt_lab or 0)) for r in reports)
    # Total units usually means "Good Units" (pt_units). So Total Processed = Good + Waste
    total_processed_units = total_prod_units + total_waste_units
    
    if total_processed_units > 0:
        waste_pct = (total_waste_units / total_processed_units) * 100
    else:
        waste_pct = 0.0

    # Avg Kg per Batch
    if total_prod_batches > 0:
        avg_kg_batch = total_prod_kg / total_prod_batches
    else:
        avg_kg_batch = 0.0

    # Quick Consumption Dependency (Contribution Rate)
    # Formula: (Total Consumo Rapido / Total Produced Real) * 100
    total_cons_qty = sum((r.cons_qty or 0) for r in reports)
    if total_prod_kg > 0:
        quick_consumption_pct = (total_cons_qty / total_prod_kg) * 100
    else:
        quick_consumption_pct = 0.0

    # --- Chart Data Aggregation ---
    
    # 1. Pie Chart: Top Products (by Kg)
    product_stats = {}
    for r in reports:
        name = r.article_type.split(" ")[0] if r.article_type else "Unknown" # Simple heuristic
        name = r.article_type or "Unknown" # Using full name
        product_stats[name] = product_stats.get(name, 0) + (r.kg_produced or 0) + (r.cons_qty or 0)

    # Sort descending and take top 5
    pie_data = [{"label": k, "value": v} for k, v in product_stats.items()]
    pie_data.sort(key=lambda x: x['value'], reverse=True)

    # 2. Historical Chart: Production vs Planning (Daily)
    from collections import defaultdict
    history_map = defaultdict(lambda: {'produced': 0.0, 'planned': 0.0, 'boxes': 0.0, 'units': 0})

    for r in reports:
        d_str = r.created_at.strftime("%Y-%m-%d")
        history_map[d_str]['produced'] += ((r.kg_produced or 0) + (r.cons_qty or 0))
        history_map[d_str]['boxes'] += (r.boxes or 0)
        history_map[d_str]['units'] += (r.pt_units or 0)

    for p in plans:
        if p.date:
            history_map[p.date]['planned'] += (p.kg or 0)

    # Convert to sorted list
    history_data = []
    # Sort by date
    sorted_dates = sorted(history_map.keys())
    for d in sorted_dates:
        history_data.append({
            "date": d,
            "produced": history_map[d]['produced'],
            "planned": history_map[d]['planned'],
            "boxes": history_map[d]['boxes'],
            "units": history_map[d]['units']
        })

    return {
        "total_production_batches": total_prod_batches,
        "total_production_kg": total_prod_kg,
        "total_production_units": total_prod_units,
        "total_production_boxes": total_prod_boxes,
        "total_waste_kg": total_waste_kg,
        "total_planned_batches": total_plan_batches,
        "total_planned_kg": total_plan_kg,
        "total_planned_units": total_plan_units,
        "yield_percentage": yield_pct,
        "compliance_percentage": compliance,
        "waste_percentage": waste_pct,
        "avg_kg_per_batch": avg_kg_batch,
        "pie_data": pie_data,
        "history_data": history_data
    }

@app.get("/api/visor/data")
def get_visor_data(db: Session = Depends(get_db)):
    # 1. Pending Planning
    pending_plans = db.query(models.ProductionPlanning).filter(models.ProductionPlanning.status == 'Pending').order_by(models.ProductionPlanning.id.asc()).all()
    
    # 2. Production Today
    today = datetime.date.today()
    today_start = datetime.datetime.combine(today, datetime.time.min)
    today_end = datetime.datetime.combine(today, datetime.time.max)
    
    production_reports = db.query(models.ProductionReport).filter(
        models.ProductionReport.created_at >= today_start,
        models.ProductionReport.created_at <= today_end
    ).order_by(models.ProductionReport.created_at.desc()).all()
    
    # Format
    planning_list = []
    for p in pending_plans:
        planning_list.append({
            "order_number": p.order_number or str(p.id).zfill(8),
            "date": p.date,
            "article": p.article,
            "status": "Pendiente",
            "units": p.units
        })
        
    production_list = []
    for r in production_reports:
        production_list.append({
            "order_number": str(r.order_number).zfill(8),
            "date": r.created_at.strftime("%Y-%m-%d"),
            "article": r.article_type,
            "status": "Procesado",
            "units": r.pt_units
        })
        
    return {
        "planning": planning_list,
        "production": production_list
    }

@app.get("/api/assistant/alerts")
def get_assistant_alerts(db: Session = Depends(get_db)):
    # Filter by Today
    today = datetime.date.today()
    start_of_day = datetime.datetime.combine(today, datetime.time.min)
    
    logs = db.query(models.AuditLog).filter(
        models.AuditLog.resource_type == 'dispatch',
        models.AuditLog.created_at >= start_of_day
        # Show ALL for the day, even if status is resolved
        # models.AuditLog.status != 'Ignored' 
    ).order_by(models.AuditLog.created_at.desc()).all()
    
    alerts = []
    
    for log in logs:
        # Fetch related dispatch
        try:
            dispatch = db.query(models.LogisticsDispatch).filter(models.LogisticsDispatch.id == log.resource_id).first()
            if not dispatch: continue
            
            # Parse Items for summary
            summary = []
            try:
                items = json.loads(dispatch.items_json)
                # Parse top 3
                for i in items[:3]:
                    summary.append(f"{i.get('qty', 0)} {i.get('unit', 'UNI')} - {i.get('item', 'Unknown')}")
                if len(items) > 3:
                    summary.append(f"... (+{len(items)-3} items)")
            except:
                summary = []

            # Parse Guide Ref
            ref_parts = (dispatch.document_ref or "").replace(" | ", "|").split("|")
            guide_col = ref_parts[0] if ref_parts else "S/R"
            fact_col = ref_parts[1] if len(ref_parts) > 1 else ""
            
            # Determine Status
            st = "OK"
            if log.severity in ['high', 'critical']: st = "CRÍTICO"
            elif log.severity == 'medium': st = "WARNING"
            else: st = "AI OK"

            alerts.append({
                "id": log.id,
                "client": dispatch.client_destination,
                "guide_ref": guide_col,
                "invoice_ref": fact_col,
                "status": st,
                "severity": log.severity,
                "description": log.description,
                "items": summary,
                "date": log.created_at.strftime("%d/%m %H:%M")
            })
            
        except Exception as e:
            print(f"Error processing alert {log.id}: {e}")
            continue
            
    return alerts



