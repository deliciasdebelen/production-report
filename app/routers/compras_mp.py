# app/routers/compras_mp.py
# Vista de Análisis Materia Prima vs Compras
# Cruza PT de ventas/pedidos/cotizaciones con sus componentes de MP
# y los compara contra las órdenes de compra del período.

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date, timedelta

from ..dependencies import get_db, templates, get_current_user, get_current_active_user
from ..external_db import get_external_db
from ..models import User
from ..services.mp_alert_service import (
    get_mp_demand, get_mp_purchases, calculate_mp_balance,
    send_mp_alert_to_all
)

router = APIRouter(prefix="/compras-mp", tags=["compras_mp"])


# ── Vista principal ──────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def compras_mp_view(request: Request, user: User = Depends(get_current_user)):
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("compras_mp.html", {
        "request": request,
        "user": user,
        "title": "MP vs Compras"
    })


# ── API principal ────────────────────────────────────────────────

@router.get("/api/dashboard")
async def get_dashboard(
    fecha_ini: str = Query(default=None),
    fecha_fin: str = Query(default=None),
    include_ventas: bool = Query(default=True),
    include_pedidos: bool = Query(default=True),
    include_cotizaciones: bool = Query(default=False),
    db_ext: Session = Depends(get_external_db),
    user: User = Depends(get_current_active_user)
):
    hoy = date.today()
    primer_dia_mes = hoy.replace(day=1)
    fi = fecha_ini or primer_dia_mes.isoformat()
    ff = fecha_fin or hoy.isoformat()

    errors = {}

    # ── 1. Demanda de MP derivada de documentos comerciales ──────
    demand = []
    try:
        with db_ext.connection() as conn:
            demand = get_mp_demand(
                conn, fi, ff,
                include_ventas=include_ventas,
                include_pedidos=include_pedidos,
                include_cotizaciones=include_cotizaciones
            )
    except Exception as e:
        # Fallback: intentar con la sesión directamente
        try:
            raw_conn = db_ext.get_bind().connect()
            demand = get_mp_demand(
                raw_conn, fi, ff,
                include_ventas=include_ventas,
                include_pedidos=include_pedidos,
                include_cotizaciones=include_cotizaciones
            )
            raw_conn.close()
        except Exception as e2:
            errors["demand"] = str(e2)

    # ── 2. Compras de MP en el período ───────────────────────────
    purchases = []
    try:
        with db_ext.connection() as conn:
            purchases = get_mp_purchases(conn, fi, ff)
    except Exception:
        try:
            raw_conn = db_ext.get_bind().connect()
            purchases = get_mp_purchases(raw_conn, fi, ff)
            raw_conn.close()
        except Exception as e2:
            errors["purchases"] = str(e2)

    # ── 3. Balance ───────────────────────────────────────────────
    balance = calculate_mp_balance(demand, purchases)

    # ── 4. KPIs de resumen ───────────────────────────────────────
    criticos = sum(1 for b in balance if b["semaforo"] == "rojo")
    alertas  = sum(1 for b in balance if b["semaforo"] == "amarillo")
    ok       = sum(1 for b in balance if b["semaforo"] == "verde")
    total_deficit = sum(b["deficit"] for b in balance)
    total_requerido = sum(b["requerido"] for b in balance)
    cobertura_global = round(
        ((total_requerido - total_deficit) / total_requerido * 100)
        if total_requerido > 0 else 100.0, 1
    )

    return {
        "kpis": {
            "total_articulos": len(balance),
            "criticos": criticos,
            "alertas": alertas,
            "ok": ok,
            "total_deficit": round(total_deficit, 2),
            "cobertura_global_pct": cobertura_global,
        },
        "balance": balance,
        "meta": {
            "fecha_ini": fi,
            "fecha_fin": ff,
            "include_ventas": include_ventas,
            "include_pedidos": include_pedidos,
            "include_cotizaciones": include_cotizaciones,
        },
        "errors": errors
    }


@router.get("/api/debug/formulas")
async def debug_formulas(
    db: Session = Depends(get_external_db),
    user: User = Depends(get_current_active_user)
):
    """Diagnóstico: qué tablas de fórmulas están disponibles."""
    results = {}
    candidates = [
        "saFormulaArticulo", "saFormulaArticuloReng",
        "saArticuloComp", "saArticuloCompReng",
        "saOrdenCompra", "saOrdenCompraReng",
        "saPresupuestoVenta", "saPresupuestoVentaReng",
    ]
    for tabla in candidates:
        try:
            count = db.execute(
                text(f"SELECT COUNT(*) as c FROM {tabla}")
            ).fetchone()
            results[tabla] = {"exists": True, "count": int(count.c) if count else 0}
        except Exception as e:
            results[tabla] = {"exists": False, "error": str(e)[:80]}
    return results


@router.post("/api/send-alert-now")
async def trigger_alert_now(
    fecha_ini: str = Query(default=None),
    fecha_fin: str = Query(default=None),
    db: Session = Depends(get_db),
    db_ext: Session = Depends(get_external_db),
    user: User = Depends(get_current_active_user)
):
    """Dispara el reporte de alerta MP de forma inmediata."""
    if user.role != 4:
        from fastapi import HTTPException
        raise HTTPException(403, "Solo administradores pueden disparar alertas manuales")
    
    hoy = date.today()
    fi = fecha_ini or hoy.replace(day=1).isoformat()
    ff = fecha_fin or hoy.isoformat()
    
    try:
        raw_conn = db_ext.get_bind().connect()
        demand = get_mp_demand(raw_conn, fi, ff)
        purchases = get_mp_purchases(raw_conn, fi, ff)
        raw_conn.close()
    except Exception as e:
        return {"success": False, "error": str(e)}
    
    balance = calculate_mp_balance(demand, purchases)
    result = send_mp_alert_to_all(db, balance, hoy.strftime("%d/%m/%Y"))
    return {"success": True, "result": result}
