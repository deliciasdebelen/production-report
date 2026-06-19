import os
import json
import logging
import pathlib
import datetime

from fastapi import FastAPI, Request, Depends, HTTPException, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text

from . import models, schemas, auth_utils
from .database import engine, Base, get_db, SessionLocal
from .external_db import external_engine
from .dependencies import get_current_user, get_current_active_user, templates
from .auth_utils import create_session_token, SESSION_COOKIE

logger = logging.getLogger(__name__)


def _load_env_startup():
    env_path = pathlib.Path("/app/.env")
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()
        except Exception as e:
            print(f"Error loading /app/.env at startup: {e}")


_load_env_startup()

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Reporte de Produccion")

# ── Router Imports ───────────────────────────────────────────

from .routers import (
    external, traslados, visor, inventory, logistics, reports,
    maintenance, discuss, ventas, administracion, sales, purchasing,
    support, export, ai_solver, assistant, semaforo, semaforo2,
    compras_mp, telegram_admin, automation_admin, mismatch_admin, projects,
    alerts, backups, cxc, bancos_config, tasa_bcv,
    production, planning, dashboard,
)

routers = [
    external, traslados, visor, inventory, logistics, reports,
    maintenance, discuss, ventas, administracion, sales, purchasing,
    support, export, ai_solver, assistant, semaforo, semaforo2,
    compras_mp, telegram_admin, automation_admin, mismatch_admin, projects,
    alerts, backups, cxc, bancos_config, tasa_bcv,
    production, planning, dashboard,
]

for r in routers:
    app.include_router(r.router)

from app.utils_id import get_next_order_number
from app.services.automation_scheduler import setup_scheduler, scheduler
from app.services.mismatch_scheduler import setup_mismatch_scheduler

# ── Helpers ──────────────────────────────────────────────────

EXPOSED_KEYS = [
    "HOST", "PORT", "REDIS_URL", "DATABASE_URL",
    "FM_BASE_URL", "FM_TOKEN",
    "SQLSRV_HOST_CXC", "PROFIT_DB", "PROFIT_USER", "PROFIT_PWD",
    "SECRET_KEY",
    "OCR_IA_PROVIDER", "GEMINI_API_KEY", "OLLAMA_API_URL", "OLLAMA_MODEL",
]

SENSITIVE = {
    "SECRET_KEY", "FM_TOKEN", "TELEGRAM_BOT_TOKEN", "PROFIT_PWD",
    "BNC_MASTER_KEY", "BNC_CLIENT_GUID", "GEMINI_API_KEY",
}

ENV_FILE = pathlib.Path("/app/.env")


# ── API Endpoints ────────────────────────────────────────────

@app.get("/api/next-id/{model_name}")
def get_next_id(model_name: str, db: Session = Depends(get_db)):
    model = None
    if model_name == "planning":
        model = models.ProductionPlanning
    elif model_name == "production":
        model = models.ProductionReport

    if model:
        return {"next_id": get_next_order_number(db, model)}
    return {"next_id": 1}


@app.get("/api/debug/db-connection")
def debug_db_connection(user: models.User = Depends(get_current_active_user)):
    try:
        with external_engine.connect() as conn:
            result = conn.execute(text("SELECT @@VERSION")).fetchone()
            return {"status": "ok", "connected": True, "version": str(result[0])[:80]}
    except Exception as e:
        return {"status": "error", "connected": False, "details": str(e)}


@app.get("/api/debug/pg-connection")
def debug_pg_connection(user: models.User = Depends(get_current_active_user)):
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()")).fetchone()
            return {"status": "ok", "connected": True, "version": str(result[0])[:80]}
    except Exception as e:
        return {"status": "error", "connected": False, "details": str(e)}


@app.post("/api/debug/test-gemini")
async def test_gemini_endpoint(request: Request, user: models.User = Depends(get_current_user)):
    try:
        data = await request.json()
        api_key = data.get("api_key", "").strip()

        mask_chars = {"•", "●"}
        if not api_key or all(c in mask_chars for c in api_key):
            api_key = os.getenv("GEMINI_API_KEY", "")

        if not api_key:
            return {"status": "error", "message": "API Key vacía"}

        import urllib.request
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=8) as response:
            resp_data = json.loads(response.read().decode())
            if "models" in resp_data:
                return {"status": "ok", "model": "gemini-1.5-flash / gemini-2.5-flash"}
            return {"status": "error", "message": "Respuesta inesperada de Google API"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/debug/test-ollama")
async def test_ollama_endpoint(request: Request, user: models.User = Depends(get_current_user)):
    try:
        data = await request.json()
        url = data.get("url", "").strip() or "http://localhost:11434"
        model = data.get("model", "").strip()

        import urllib.request
        tags_url = f"{url.rstrip('/')}/api/tags"
        req = urllib.request.Request(tags_url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            resp_data = json.loads(response.read().decode())
            models_list = [m.get("name") for m in resp_data.get("models", [])]

            if model in models_list or f"{model}:latest" in models_list:
                return {"status": "ok", "model": model}

            return {
                "status": "warning",
                "message": (
                    f"Ollama responde, pero el modelo '{model}' no está descargado. "
                    f"Modelos disponibles: {', '.join(models_list) or 'Ninguno'}"
                ),
            }
    except Exception as e:
        return {"status": "error", "message": f"No se pudo conectar a Ollama: {str(e)}"}


@app.get("/api/sys/config")
async def get_sys_config(user: models.User = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not Authenticated")
    config = {}
    for key in EXPOSED_KEYS:
        val = os.getenv(key, "")
        if key in SENSITIVE and val:
            config[key] = "***"
        else:
            config[key] = val

    try:
        from app.services.profit_cxc_service import PROFIT_HOST, PROFIT_DB, PROFIT_USER
        config["PROFIT_HOST"] = PROFIT_HOST
        config["PROFIT_DB"] = PROFIT_DB
        config["PROFIT_USER"] = PROFIT_USER
    except Exception:
        pass

    return {"status": "ok", "config": config}


@app.post("/api/sys/config")
async def post_sys_config(request: Request, user: models.User = Depends(get_current_active_user)):
    if user.role != 4:
        raise HTTPException(status_code=403, detail="Solo administradores")
    try:
        data = await request.json()
        if not data:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Sin datos"})

        mask_chars = {"•", "●"}
        updates = {k: v for k, v in data.items() if v and not all(c in mask_chars for c in str(v))}
        if not updates:
            return {"status": "ok", "message": "Sin cambios efectivos que guardar."}

        for k, v in updates.items():
            os.environ[k] = str(v)

        env_lines = []
        written_keys = set()
        if ENV_FILE.exists():
            env_lines = ENV_FILE.read_text(encoding="utf-8").splitlines()

        new_lines = []
        for line in env_lines:
            stripped = line.strip()
            if stripped.startswith("#") or "=" not in stripped:
                new_lines.append(line)
                continue
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                written_keys.add(key)
            else:
                new_lines.append(line)

        for k, v in updates.items():
            if k not in written_keys:
                new_lines.append(f"{k}={v}")

        try:
            ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            saved_to_file = True
        except Exception as fe:
            saved_to_file = False
            logger.warning(f"No se pudo escribir .env: {fe}")

        msg = f"Configuración actualizada ({', '.join(updates.keys())})"
        if saved_to_file:
            msg += ". Cambios persistidos en .env"
        else:
            msg += ". Solo en memoria (reiniciar para persistir)"

        return {"status": "ok", "message": msg, "updated": list(updates.keys())}
    except Exception as e:
        logger.error(f"post_sys_config error: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


app.mount("/static", StaticFiles(directory="app/static"), name="static")


# ── Startup ──────────────────────────────────────────────────

@app.on_event("startup")
def startup_db_client():
    db = SessionLocal()
    try:
        default_roles = [
            (1, "KPI"), (2, "Produccion"), (3, "Planificacion"),
            (4, "Administrador"), (5, "Almacen"), (6, "Inventario"),
            (7, "Patrimonial"), (8, "Director"), (9, "Soporte (Solo Crear)"),
        ]
        for role_id, role_name in default_roles:
            exists = db.query(models.Role).filter(models.Role.id == role_id).first()
            if not exists:
                db.add(models.Role(id=role_id, name=role_name, permissions="{}"))
        db.commit()

        admin = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin:
            hashed = auth_utils.get_password_hash("admin")
            admin = models.User(username="admin", password_hash=hashed, role=4)
            db.add(admin)
            db.commit()
    except Exception as e:
        print(f"[startup] Warning during init: {e}")
        db.rollback()
    finally:
        db.close()

    service_type = os.getenv("SERVICE_TYPE", "bancos").strip().lower()
    if service_type == "tasa_bcv":
        print("[Startup] Starting Tasa BCV microservice: starting BCV scheduler...")
        from app.services.bcv_tasa_service import setup_bcv_scheduler
        setup_bcv_scheduler(scheduler)
        try:
            scheduler.start()
        except Exception as e:
            print(f"[Startup] Warning starting scheduler: {e}")
    elif service_type == "bancos":
        print("[Startup] Starting API Bancos service: starting banking schedulers...")
        setup_scheduler()
        setup_mismatch_scheduler(scheduler)
    else:
        print(f"[Startup] Starting microservice {service_type} (no schedulers started)")


# ── Health Check ─────────────────────────────────────────────

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    service_type = os.getenv("SERVICE_TYPE", "bancos").strip().lower()
    status_details = {}
    healthy = True

    try:
        db.execute(text("SELECT 1"))
        status_details["postgres"] = "OK"
    except Exception as e:
        status_details["postgres"] = f"FAIL: {e}"
        healthy = False

    if service_type == "tasa_bcv":
        from app.services import bcv_tasa_service as bcvsvc
        conn_ok, conn_msg = bcvsvc.test_profit_connection()
        status_details["profit_satasa"] = "OK" if conn_ok else f"FAIL: {conn_msg}"
        if not conn_ok:
            healthy = False
    else:
        from app.services import profit_cxc_service as cxc_svc
        if not cxc_svc.PROFIT_INTEGRATION_ENABLED:
            status_details["profit_cxc"] = "DISABLED"
        else:
            profit_ok = cxc_svc.test_connection()
            status_details["profit_cxc"] = "OK" if profit_ok else "FAIL"
            if not profit_ok:
                healthy = False

        import requests
        try:
            resp = requests.get("http://tasa-bcv:8000/login", timeout=3)
            status_details["tasa_bcv_microservice"] = "OK" if resp.status_code == 200 else f"HTTP {resp.status_code}"
        except Exception as e:
            status_details["tasa_bcv_microservice"] = f"FAIL: {e}"

    if healthy:
        return {"status": "healthy", "service": service_type, "details": status_details}

    raise HTTPException(
        status_code=500,
        detail={"status": "unhealthy", "service": service_type, "details": status_details},
    )


# ── Auth Views ───────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return RedirectResponse(url="/login?error=invalid_user", status_code=303)
    if not auth_utils.verify_password(password, user.password_hash):
        return RedirectResponse(url="/login?error=invalid_password", status_code=303)

    url = "/support/create" if user.role == 9 else "/"
    response = RedirectResponse(url=url, status_code=303)
    token = create_session_token(user.id)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,  # 7 days
    )
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie(SESSION_COOKIE)
    response.delete_cookie("user_id")
    return response


# ── Page Views ───────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, user: models.User = Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login")
    if user.role == 9:
        return RedirectResponse("/support/create")
    return templates.TemplateResponse("index.html", {"request": request, "title": "Home", "user": user})


@app.get("/sistema", response_class=HTMLResponse)
async def view_sistema_dashboard(request: Request, user: models.User = Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login")
    if user.role != 4:
        return templates.TemplateResponse("403.html", {"request": request, "user": user})
    return templates.TemplateResponse(
        "administracion/index.html",
        {"request": request, "title": "Administración", "user": user},
    )


@app.get("/report", response_class=HTMLResponse)
async def view_report(request: Request, user: models.User = Depends(get_current_active_user)):
    if user.role not in [2, 4]:
        return templates.TemplateResponse("403.html", {"request": request, "user": user})
    return templates.TemplateResponse("report.html", {"request": request, "title": "Reporte", "user": user})


@app.get("/planning", response_class=HTMLResponse)
async def view_planning(request: Request, user: models.User = Depends(get_current_active_user)):
    if user.role not in [3, 4]:
        return templates.TemplateResponse("403.html", {"request": request, "user": user})
    return templates.TemplateResponse(
        "planning.html",
        {"request": request, "title": "Orden de Planificación", "user": user},
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def view_dashboard(request: Request, user: models.User = Depends(get_current_active_user)):
    return templates.TemplateResponse("dashboard.html", {"request": request, "title": "Dashboard", "user": user})


@app.get("/visor", response_class=HTMLResponse)
async def view_visor(request: Request, user: models.User = Depends(get_current_active_user)):
    return templates.TemplateResponse(
        "visor.html",
        {"request": request, "title": "Visor de Producción", "user": user},
    )


@app.get("/assistant", response_class=HTMLResponse)
async def view_assistant(request: Request, user: models.User = Depends(get_current_active_user)):
    return templates.TemplateResponse(
        "assistant.html",
        {"request": request, "title": "Asistente", "user": user},
    )


# ── Assistant Alerts ─────────────────────────────────────────

@app.get("/api/assistant/alerts")
def get_assistant_alerts(db: Session = Depends(get_db)):
    today = datetime.date.today()
    start_of_day = datetime.datetime.combine(today, datetime.time.min)

    logs = (
        db.query(models.AuditLog)
        .filter(
            models.AuditLog.resource_type == "dispatch",
            models.AuditLog.created_at >= start_of_day,
        )
        .order_by(models.AuditLog.created_at.desc())
        .all()
    )

    alerts = []
    for log in logs:
        try:
            dispatch = (
                db.query(models.LogisticsDispatch)
                .filter(models.LogisticsDispatch.id == log.resource_id)
                .first()
            )
            if not dispatch:
                continue

            summary = []
            try:
                items = json.loads(dispatch.items_json)
                for i in items[:3]:
                    summary.append(f"{i.get('qty', 0)} {i.get('unit', 'UNI')} - {i.get('item', 'Unknown')}")
                if len(items) > 3:
                    summary.append(f"... (+{len(items) - 3} items)")
            except Exception:
                summary = []

            ref_parts = (dispatch.document_ref or "").replace(" | ", "|").split("|")
            guide_col = ref_parts[0] if ref_parts else "S/R"
            fact_col = ref_parts[1] if len(ref_parts) > 1 else ""

            if log.severity in ["high", "critical"]:
                st = "CRÍTICO"
            elif log.severity == "medium":
                st = "WARNING"
            else:
                st = "AI OK"

            alerts.append({
                "id": log.id,
                "client": dispatch.client_destination,
                "guide_ref": guide_col,
                "invoice_ref": fact_col,
                "status": st,
                "severity": log.severity,
                "description": log.description,
                "items": summary,
                "date": log.created_at.strftime("%d/%m %H:%M"),
            })
        except Exception as e:
            print(f"Error processing alert {log.id}: {e}")

    return alerts
