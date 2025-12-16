from fastapi import FastAPI, Request, Depends, HTTPException, Form, Response, Cookie, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import shutil
import os
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from . import models, schemas, auth_utils
from .database import SessionLocal, engine
from .routers import external, traslados
from typing import Optional
import datetime

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Reporte de Produccion")

app.include_router(external.router)
app.include_router(traslados.router)
from .routers import logistics
app.include_router(logistics.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
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
    if not user or not auth_utils.verify_password(password, user.password_hash):
        return RedirectResponse(url="/login?error=Invalid credentials", status_code=303)
    
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
    if user.role not in [3, 4]: # 3=Plan, 4=Admin
        return templates.TemplateResponse("403.html", {"request": request, "user": user})
    return templates.TemplateResponse("planning.html", {"request": request, "title": "Planificación", "user": user})

@app.get("/dashboard", response_class=HTMLResponse)
async def view_dashboard(request: Request, user: models.User = Depends(get_current_active_user)):
    return templates.TemplateResponse("dashboard.html", {"request": request, "title": "Dashboard", "user": user})

@app.get("/assistant", response_class=HTMLResponse)
async def view_assistant(request: Request, user: models.User = Depends(get_current_active_user)):
     return templates.TemplateResponse("assistant.html", {"request": request, "title": "Asistente", "user": user})

@app.get("/maintenance", response_class=HTMLResponse)
async def view_maintenance(request: Request, db: Session = Depends(get_db), user: models.User = Depends(get_current_active_user)):
    if user.role != 4:
        return templates.TemplateResponse("403.html", {"request": request, "user": user})
    
    users = db.query(models.User).all()
    return templates.TemplateResponse("maintenance.html", {"request": request, "title": "Mantenimiento", "user": user, "users": users})

# --- Maintenance API ---
@app.post("/maintenance/users")
async def create_user(username: str = Form(...), password: str = Form(...), role: int = Form(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    if current_user.role != 4: raise HTTPException(403)
    hashed = auth_utils.get_password_hash(password)
    new_user = models.User(username=username, password_hash=hashed, role=role)
    try:
        db.add(new_user)
        db.commit()
    except:
        return RedirectResponse("/maintenance?error=User exists", status_code=303)
    return RedirectResponse("/maintenance", status_code=303)

@app.post("/maintenance/users/delete")
async def delete_user(user_id: int = Form(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    if current_user.role != 4: raise HTTPException(403)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user and user.username != "admin": # Prevent deleting default admin
        db.delete(user)
        db.commit()
    return RedirectResponse("/maintenance", status_code=303)

    return RedirectResponse("/maintenance", status_code=303)

@app.post("/maintenance/data/preview")
async def preview_data(
    table: str = Form(...),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if current_user.role != 4: raise HTTPException(403)

    model = None
    date_field = None
    if table == 'production': 
        model = models.ProductionReport
        date_field = models.ProductionReport.created_at # TODO: Cast to date if needed, or use string filtering
    elif table == 'planning': 
        model = models.ProductionPlanning
        date_field = models.ProductionPlanning.date # This is a string YYYY-MM-DD
    
    if not model: return {"error": "Invalid table"}

    query = db.query(model)

    # Date Filtering
    if start_date:
        if table == 'planning':
            query = query.filter(date_field >= start_date)
        else:
             # Simplistic string comparison for datetime might work if format matches, otherwise need cast
             # specific for sqlite/sql server. For now, assuming basic string comparison works for ISO dates
             pass 
    if end_date:
        if table == 'planning':
             query = query.filter(date_field <= end_date)

    data = query.limit(100).all()
    return data

@app.get("/maintenance/report/print", response_class=HTMLResponse)
async def print_report(
    request: Request,
    type: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user)
):
    # Authorization Logic
    allowed = False
    if user.role == 4: # Admin sees all
        allowed = True
    elif type == "planning" and user.role == 3: # Plan sees Plan
        allowed = True
    elif type == "production" and user.role == 2: # Prod sees Prod
        allowed = True
    
    if not allowed:
        return templates.TemplateResponse("403.html", {"request": request, "user": user})

    rows = []
    columns = []
    title = ""
    
    # 1. USERS REPORT
    if type == "users":
        title = "Reporte de Usuarios del Sistema"
        users_list = db.query(models.User).all()
        columns = ["ID", "Usuario", "Rol", "Hash (Parcial)"]
        
        role_map = {1: "KPI (Lectura)", 2: "Producción", 3: "Planificación", 4: "Administrador"}
        
        for u in users_list:
            r_name = role_map.get(u.role, "Desconocido")
            rows.append([u.id, u.username, r_name, u.password_hash[:10] + "..."])

    # 2. PLANNING REPORT
    elif type == "planning":
        title = "Reporte de Planificación de Producción"
        columns = ["ID", "Fecha Planificada", "Fecha Asignación", "Artículo", "Batches", "Kg Plan", "Unidades"]
        
        query = db.query(models.ProductionPlanning)
        if start_date: query = query.filter(models.ProductionPlanning.date >= start_date)
        if end_date: query = query.filter(models.ProductionPlanning.date <= end_date)
        
        results = query.order_by(models.ProductionPlanning.date.desc()).all()
        
        for p in results:
            rows.append([
                p.id,
                p.date,
                p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "-",
                f"{p.article} - {p.presentation}",
                p.batches,
                f"{p.kg:.2f}",
                p.units
            ])

    # 3. PRODUCTION REPORT
    elif type == "production":
        title = "Reporte de Producción Ejecutada"
        columns = ["ID", "Fecha Registro", "Artículo", "Presentación", "Batches", "Kg Prod", "Unidades", "Cajas", "Mermas (Und)"]
        
        query = db.query(models.ProductionReport)
        
        # Datetime filtering logic
        if start_date:
            try:
                sd = datetime.datetime.strptime(start_date, "%Y-%m-%d")
                query = query.filter(models.ProductionReport.created_at >= sd)
            except: pass
        
        if end_date:
            try:
                ed = datetime.datetime.strptime(end_date, "%Y-%m-%d")
                ed_end = datetime.datetime.combine(ed, datetime.time.max)
                query = query.filter(models.ProductionReport.created_at <= ed_end)
            except: pass
            
        results = query.order_by(models.ProductionReport.created_at.desc()).all()
        
        for r in results:
            waste = (r.pt_burned or 0) + (r.pt_lab or 0)
            rows.append([
                r.id,
                r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "-",
                r.article_type,
                r.presentation,
                r.batch_qty,
                f"{r.kg_produced:.2f}",
                r.pt_units,
                r.boxes,
                waste
            ])

    return templates.TemplateResponse("print_report.html", {
        "request": request,
        "title": title,
        "columns": columns,
        "rows": rows,
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "date_range": f"{start_date or 'Inicio'} al {end_date or 'Fin'}" if (start_date or end_date) else "Periodo Completo"
    })

@app.post("/maintenance/data/delete")
async def delete_data(
    table: str = Form(...), 
    action: str = Form(...), 
    id: Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_active_user)
):
    if current_user.role != 4: raise HTTPException(403)
    
    model = None
    if table == 'production': model = models.ProductionReport
    elif table == 'planning': model = models.ProductionPlanning
    
    if not model: return RedirectResponse("/maintenance?error=Invalid table", status_code=303)

    query = db.query(model)
    deleted_count = 0

    if action == 'all':
        # Apply filters if present
        if start_date and table == 'planning':
            query = query.filter(models.ProductionPlanning.date >= start_date)
        if end_date and table == 'planning':
            query = query.filter(models.ProductionPlanning.date <= end_date)
        
        # Check count before delete
        count = query.count()
        if count == 0:
             return RedirectResponse("/maintenance?message=No hay datos para eliminar", status_code=303)
        
        deleted_count = query.delete(synchronize_session=False)

    elif action == 'one' and id:
        query = query.filter(model.id == id)
        if query.count() == 0:
             return RedirectResponse("/maintenance?message=Registro no encontrado", status_code=303)
        deleted_count = query.delete(synchronize_session=False)
        
    db.commit()
    return RedirectResponse(f"/maintenance?message=Se eliminaron {deleted_count} registros", status_code=303)

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
    custom_created_at: Optional[str] = Form(None), # Date string
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Handle File Upload
    image_path = None
    if mp_waste_image and mp_waste_image.filename:
        upload_dir = "app/static/uploads/waste"
        os.makedirs(upload_dir, exist_ok=True)
        # Generate safe filename
        ext = os.path.splitext(mp_waste_image.filename)[1]
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        safe_name = f"waste_{timestamp}{ext}"
        file_location = f"{upload_dir}/{safe_name}"
        
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(mp_waste_image.file, buffer)
        
        # Save relative path for URL access
        image_path = f"/static/uploads/waste/{safe_name}"

    # Handle Date Override
    created_at_val = None
    if custom_created_at and current_user.role == 4:
        try:
             d = datetime.datetime.strptime(custom_created_at, "%Y-%m-%d")
             created_at_val = datetime.datetime.combine(d.datetime.min.time()) # Error in previous logic? no wait combine needs date and time
             # Fixed logic:
             created_at_val = datetime.datetime.combine(d.date(), datetime.time.min)
        except:
             pass

    # Generate Order Number
    order_number = generate_next_order_number(db, models.ProductionReport)

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
        order_number=order_number
    )
    
    if created_at_val:
        db_report.created_at = created_at_val

    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report

@app.get("/api/production", response_model=list[schemas.ProductionReport])
def read_production_reports(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    reports = db.query(models.ProductionReport).order_by(models.ProductionReport.created_at.desc()).offset(skip).limit(limit).all()
    return reports

@app.post("/api/planning", response_model=schemas.ProductionPlanning)
def create_planning(plan: schemas.ProductionPlanningCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    if plan.date < today_str and current_user.role != 4:
        raise HTTPException(status_code=403, detail="Solo administradores pueden planificar fechas pasadas")

    plan_data = plan.dict()
    plan_data['order_number'] = generate_next_order_number(db, models.ProductionPlanning)

    db_plan = models.ProductionPlanning(**plan_data)
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan

@app.get("/api/planning", response_model=list[schemas.ProductionPlanning])
def read_planning(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    plans = db.query(models.ProductionPlanning).offset(skip).limit(limit).all()
    return plans

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

    total_prod_batches = sum(r.batch_qty for r in reports)
    # Total Kg = Kg Produced (Batches) + Consumo Rapido (Quick Consumption)
    total_prod_kg = sum((r.kg_produced + r.cons_qty) for r in reports)
    total_prod_units = sum(r.pt_units for r in reports)
    total_prod_boxes = sum(r.boxes for r in reports) 
    total_waste_kg = sum(r.mp_waste_kg for r in reports)

    total_plan_batches = sum(p.batches for p in plans)
    total_plan_kg = sum(p.kg for p in plans)
    total_plan_units = sum(p.units for p in plans)

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
    total_waste_units = sum((r.pt_burned + r.pt_lab) for r in reports)
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

    # --- Chart Data Aggregation ---
    
    # 1. Pie Chart: Top Products (by Kg)
    product_stats = {}
    for r in reports:
        name = r.article_type.split(" ")[0] if r.article_type else "Unknown" # Simple heuristic
        name = r.article_type # Using full name
        product_stats[name] = product_stats.get(name, 0) + r.kg_produced + r.cons_qty

    # Sort descending and take top 5
    pie_data = [{"label": k, "value": v} for k, v in product_stats.items()]
    pie_data.sort(key=lambda x: x['value'], reverse=True)

    # 2. Historical Chart: Production vs Planning (Daily)
    from collections import defaultdict
    history_map = defaultdict(lambda: {'produced': 0.0, 'planned': 0.0, 'boxes': 0.0, 'units': 0})

    for r in reports:
        d_str = r.created_at.strftime("%Y-%m-%d")
        history_map[d_str]['produced'] += (r.kg_produced + r.cons_qty)
        history_map[d_str]['boxes'] += r.boxes
        history_map[d_str]['units'] += r.pt_units

    for p in plans:
        history_map[p.date]['planned'] += p.kg

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
