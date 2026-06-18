from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import datetime
from sqlalchemy.orm import Session
from app.database import pg_engine, SessionLocal
from app.models import Base, ConsistencyLog
from app.scheduler import start_scheduler, scheduler, run_consistency_check
import logging
import json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Create tables in PostgreSQL on startup (creates consistency_log table if not exists)
Base.metadata.create_all(bind=pg_engine)

app = FastAPI(title="Consistency Monitor Microservice")

# Static files & templates setup
os.makedirs("app/templates", exist_ok=True)
templates = Jinja2Templates(directory="app/templates")

@app.on_event("startup")
def startup_event():
    start_scheduler()

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})

@app.get("/logs")
async def get_logs():
    db = SessionLocal()
    try:
        # Get latest 100 runs
        logs = db.query(ConsistencyLog).order_by(ConsistencyLog.id.desc()).limit(100).all()
        result = []
        for log in logs:
            try:
                details_parsed = json.loads(log.details) if log.details else []
            except:
                details_parsed = [{"error": log.details}]
                
            result.append({
                "id": log.id,
                "execution_date": log.execution_date.strftime("%Y-%m-%d %H:%M:%S"),
                "initiated_by": log.initiated_by,
                "status": log.status,
                "duration_seconds": round(log.duration_seconds, 2) if log.duration_seconds else 0,
                "details": details_parsed
            })
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()

@app.get("/scheduler/status")
async def get_scheduler_status():
    job = scheduler.get_job("consistency_cron")
    if not job:
        return JSONResponse(content={"active": False, "next_run": None})
    
    next_run = job.next_run_time
    return JSONResponse(content={
        "active": scheduler.running,
        "next_run": next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else None
    })

# Store manual execution state to prevent parallel manual runs
manual_running = False

def run_manual_bg(b_corregir: int, username: str):
    global manual_running
    try:
        run_consistency_check(b_corregir, f"User: {username}")
    finally:
        manual_running = False

@app.post("/run")
async def trigger_run(request: Request, background_tasks: BackgroundTasks):
    global manual_running
    if manual_running:
        return JSONResponse(status_code=400, content={"error": "Ya hay una ejecución manual en curso."})
        
    data = await request.json()
    b_corregir = int(data.get("b_corregir", 0))
    username = data.get("username", "Administrador")
    
    manual_running = True
    background_tasks.add_task(run_manual_bg, b_corregir, username)
    return JSONResponse(content={"message": f"Validación iniciada en segundo plano por {username}"})
