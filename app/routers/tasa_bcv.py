"""
Router Tasa BCV — Scraping y Sincronización de Tasas Oficiales (USD/EUR)
URL: /administracion/tasaBCV
"""
from fastapi import APIRouter, Request, Depends, Body, Query
from fastapi.responses import HTMLResponse, JSONResponse
from app.dependencies import get_current_user, templates
from app import models
from app.services import bcv_tasa_service as bcvsvc
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Set the router prefix to /administracion to support both /tasaBCV and /tasabcv
router = APIRouter(prefix="/administracion", tags=["tasa-bcv"])


# ─────────────────────────────────────────────
# VISTAS HTML
# ─────────────────────────────────────────────

@router.get("/tasaBCV", response_class=HTMLResponse)
@router.get("/tasaBCV/", response_class=HTMLResponse)
@router.get("/tasabcv", response_class=HTMLResponse)
@router.get("/tasabcv/", response_class=HTMLResponse)
async def view_tasa_bcv(
    request: Request,
    user: models.User = Depends(get_current_user)
):
    """Panel principal de Tasa BCV."""
    return templates.TemplateResponse("administracion/tasa_bcv.html", {
        "request": request,
        "title": "Tasa de Cambio BCV",
        "user": user,
    })


# ─────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────

@router.get("/tasaBCV/api/status")
@router.get("/tasabcv/api/status")
def api_status(user: models.User = Depends(get_current_user)):
    """Retorna el estado de la última ejecución, rastro de logs y tasas actuales."""
    try:
        # Raspado en vivo: scrape_tasas_bcv returns Tuple[Dict[str, Optional[float]], Optional[date]]
        scraped_res, fecha_valor = bcvsvc.scrape_tasas_bcv()
        if not scraped_res:
            scraped_res = {"USD": None, "EUR": None}
    except Exception as e:
        logger.error(f"Error scraping bcv: {e}")
        scraped_res = {"USD": None, "EUR": None}
        fecha_valor = None

    # Fallback to the latest registered rate in Profit for each currency if missing
    tasas_bcv_flat = {}
    for co_mone in ["USD", "EUR"]:
        val = scraped_res.get(co_mone)
        if val is None:
            val = bcvsvc._leer_tasa_anterior(co_mone)
        tasas_bcv_flat[co_mone] = val

    # Estado del ciclo y rastro
    estado = bcvsvc.estado_ciclo()
    rastro = bcvsvc.obtener_rastro(limite=100)

    # Buscar tasas actuales en Profit para hoy y el siguiente día hábil
    from datetime import date
    hoy = date.today()
    f_aplic = bcvsvc._fecha_aplicacion(hoy)
    
    # Obtener la tasa activa hoy (que puede ser la de ayer o la del ultimo dia habil anterior)
    usd_tasa_hoy, usd_fecha_hoy = bcvsvc.obtener_tasa_activa_y_fecha_profit("USD", hoy)
    eur_tasa_hoy, eur_fecha_hoy = bcvsvc.obtener_tasa_activa_y_fecha_profit("EUR", hoy)

    tasas_profit_hoy = {
        "USD": usd_tasa_hoy,
        "EUR": eur_tasa_hoy
    }
    
    tasas_profit_aplic = {
        "USD": bcvsvc.obtener_tasa_actual_profit("USD", f_aplic),
        "EUR": bcvsvc.obtener_tasa_actual_profit("EUR", f_aplic)
    }

    tasas_latest_profit = {
        "USD": bcvsvc._leer_tasa_anterior("USD"),
        "EUR": bcvsvc._leer_tasa_anterior("EUR")
    }

    return {
        "status": "ok",
        "tasas_bcv": tasas_bcv_flat,
        "fecha_valor_bcv": fecha_valor.isoformat() if fecha_valor else None,
        "estado_ciclo": estado,
        "rastro": rastro,
        "fechas": {
            "hoy": hoy.isoformat(),
            "aplicacion": f_aplic.isoformat()
        },
        "tasas_profit": {
            "hoy": tasas_profit_hoy,
            "aplicacion": tasas_profit_aplic,
            "latest": tasas_latest_profit,
            "fechas": {
                "hoy_USD": usd_fecha_hoy.isoformat() if usd_fecha_hoy else None,
                "hoy_EUR": eur_fecha_hoy.isoformat() if eur_fecha_hoy else None
            }
        }
    }


@router.post("/tasaBCV/api/sync")
@router.post("/tasabcv/api/sync")
def api_sync(
    forzar: bool = Query(True),
    user: models.User = Depends(get_current_user)
):
    """Ejecuta manualmente el raspado del BCV y la actualización en Profit."""
    try:
        res = bcvsvc.ejecutar_ciclo_bcv(forzar=forzar)
        return {"status": "ok", "result": res}
    except Exception as e:
        logger.error(f"Error en sincronización manual BCV: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Error ejecutando ciclo: {str(e)}"}
        )


@router.get("/tasaBCV/api/config")
@router.get("/tasabcv/api/config")
def api_get_config(user: models.User = Depends(get_current_user)):
    """Retorna la configuración actual de conexión (password enmascarado)."""
    cfg = bcvsvc.load_bcv_config()
    masked = dict(cfg)
    if masked.get("password"):
        masked["password"] = "••••••••"
    return {"status": "ok", "config": masked}


@router.post("/tasaBCV/api/config")
@router.post("/tasabcv/api/config")
def api_save_config(
    data: dict = Body(...),
    user: models.User = Depends(get_current_user)
):
    """Guarda la nueva configuración de la BD Profit (solo Admins)."""
    # Verificar rol de administrador (role 4)
    is_admin = user.role == 4 or (
        hasattr(user, 'extra_roles') and 
        any(getattr(ur, 'role_id', None) == 4 for ur in (user.extra_roles or []))
    )
    if not is_admin:
        return JSONResponse(
            status_code=403,
            content={"status": "forbidden", "message": "Solo administradores pueden cambiar esta configuración."}
        )

    cfg = bcvsvc.load_bcv_config()
    for field in ["host", "instance", "database", "user", "port"]:
        if field in data:
            cfg[field] = str(data[field]).strip()

    pwd = data.get("password")
    if pwd and pwd != "••••••••":
        cfg["password"] = pwd

    ok = bcvsvc.save_bcv_config(cfg)
    if ok:
        # Probar conexión de inmediato
        conn_ok, conn_msg = bcvsvc.test_profit_connection(cfg)
        return {
            "status": "ok",
            "message": "Configuración guardada correctamente.",
            "connection_status": {
                "ok": conn_ok,
                "message": conn_msg
            }
        }
    else:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Error al guardar la configuración."}
        )


@router.post("/tasaBCV/api/config/test")
@router.post("/tasabcv/api/config/test")
def api_test_config(
    data: dict = Body(...),
    user: models.User = Depends(get_current_user)
):
    """Prueba la conexión a Profit con la configuración suministrada sin guardarla."""
    cfg = dict(data)
    if cfg.get("password") == "••••••••":
        existing = bcvsvc.load_bcv_config()
        cfg["password"] = existing.get("password", "")

    conn_ok, conn_msg = bcvsvc.test_profit_connection(cfg)
    return {
        "status": "ok",
        "connected": conn_ok,
        "message": conn_msg
    }
