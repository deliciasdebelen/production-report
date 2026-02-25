# app/routers/semaforo.py
# Semáforo de Ventas — compara ventas del día vs. promedio 30 días

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta, date

from ..dependencies import get_db, templates, get_current_user, get_current_active_user
from ..external_db import get_external_db
from ..models import User, LogisticsDispatch

router = APIRouter(
    prefix="/semaforo",
    tags=["semaforo"],
)


def calcular_semaforo(hoy: float, promedio_30: float) -> dict:
    """
    Calcula el estado del semáforo según el % respecto al promedio 30 días.
    Verde  ≥ 90%   Amarillo  70-89%   Rojo < 70%
    """
    if promedio_30 == 0:
        return {"estado": "sin_datos", "color": "gray", "emoji": "⚪", "pct": 0}

    pct = (hoy / promedio_30) * 100
    if pct >= 90:
        estado, color, emoji, label = "verde", "#22c55e", "🟢", "En Meta"
    elif pct >= 70:
        estado, color, emoji, label = "amarillo", "#eab308", "🟡", "Alerta"
    else:
        estado, color, emoji, label = "rojo", "#ef4444", "🔴", "Bajo Meta"

    return {
        "estado": estado,
        "color": color,
        "emoji": emoji,
        "label": label,
        "pct": round(pct, 1),
        "hoy": round(hoy, 2),
        "promedio_30": round(promedio_30, 2),
        "diferencia": round(hoy - promedio_30, 2),
    }


# ── Vista HTML ────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def semaforo_view(
    request: Request,
    user: User = Depends(get_current_user)
):
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("semaforo.html", {
        "request": request,
        "user": user,
        "title": "Semáforo de Ventas"
    })


# ── API JSON ──────────────────────────────────────────────────────

@router.get("/api/estado")
async def get_estado_semaforo(
    db_ext: Session = Depends(get_external_db),
    db_local: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    """
    Retorna el estado actual del semáforo de ventas.
    Fuente primaria: saFacturaVenta (Carmal)
    Fallback: LogisticsDispatch (produccion-report local)
    """
    hoy_str = date.today().isoformat()
    hace_30 = (date.today() - timedelta(days=30)).isoformat()
    hace_60 = (date.today() - timedelta(days=60)).isoformat()

    fuente = "carmal"
    hoy_ventas = 0.0
    promedio_30 = 0.0
    top_clientes = []
    historico_7dias = []

    # ── Intentar con Carmal (mssql) ───────────────────────────────
    try:
        dialect = db_ext.bind.dialect.name

        if dialect == "mssql":
            # Ventas de HOY
            r_hoy = db_ext.execute(text("""
                SELECT ISNULL(SUM(f.monto_tot), 0) as total_hoy,
                       COUNT(DISTINCT f.doc_num) as num_facturas
                FROM saFacturaVenta f
                WHERE CAST(f.fe_emis AS DATE) = CAST(GETDATE() AS DATE)
                  AND f.anulado = 0
            """)).fetchone()
            hoy_ventas = float(r_hoy.total_hoy) if r_hoy else 0.0
            num_facturas_hoy = int(r_hoy.num_facturas) if r_hoy else 0

            # Promedio diario de los últimos 30 días (excluyendo hoy)
            r_prom = db_ext.execute(text("""
                SELECT ISNULL(SUM(f.monto_tot), 0) / NULLIF(COUNT(DISTINCT CAST(f.fe_emis AS DATE)), 0) as promedio_dia
                FROM saFacturaVenta f
                WHERE CAST(f.fe_emis AS DATE) BETWEEN :d30 AND DATEADD(day, -1, CAST(GETDATE() AS DATE))
                  AND f.anulado = 0
            """), {"d30": hace_30}).fetchone()
            promedio_30 = float(r_prom.promedio_dia) if r_prom and r_prom.promedio_dia else 0.0

            # Top 5 clientes de hoy
            r_cli = db_ext.execute(text("""
                SELECT TOP 5 c.cli_des, ISNULL(SUM(f.monto_tot), 0) as total
                FROM saFacturaVenta f
                JOIN saCliente c ON f.co_cli = c.co_cli
                WHERE CAST(f.fe_emis AS DATE) = CAST(GETDATE() AS DATE) AND f.anulado = 0
                GROUP BY c.cli_des ORDER BY total DESC
            """)).fetchall()
            top_clientes = [{"cliente": r.cli_des.strip(), "total": float(r.total)} for r in r_cli]

            # Histórico últimos 7 días
            r_hist = db_ext.execute(text("""
                SELECT CAST(fe_emis AS DATE) as dia,
                       ISNULL(SUM(monto_tot), 0) as total,
                       COUNT(DISTINCT doc_num) as facturas
                FROM saFacturaVenta
                WHERE fe_emis >= DATEADD(day, -7, GETDATE()) AND anulado = 0
                GROUP BY CAST(fe_emis AS DATE)
                ORDER BY dia DESC
            """)).fetchall()
            historico_7dias = [
                {"dia": str(r.dia), "total": float(r.total), "facturas": int(r.facturas)}
                for r in r_hist
            ]

        else:
            raise Exception("No es mssql, usar fallback")

    except Exception as e:
        # ── Fallback: LogisticsDispatch local ──────────────────────
        fuente = "local"
        num_facturas_hoy = 0

        hoy_dt = datetime.now().date()
        hace_30_dt = hoy_dt - timedelta(days=30)

        despachos_hoy = db_local.query(LogisticsDispatch).filter(
            LogisticsDispatch.created_at >= datetime.combine(hoy_dt, datetime.min.time())
        ).count()

        # Promedio contra los últimos 30 días
        import json as _json
        despachos_30 = db_local.query(LogisticsDispatch).filter(
            LogisticsDispatch.created_at >= datetime.combine(hace_30_dt, datetime.min.time()),
            LogisticsDispatch.created_at < datetime.combine(hoy_dt, datetime.min.time())
        ).all()

        total_despachos_30 = len(despachos_30)
        promedio_30 = total_despachos_30 / 30.0
        hoy_ventas = float(despachos_hoy)
        num_facturas_hoy = despachos_hoy

        historico_7dias = []

    # ── Calcular semáforo ─────────────────────────────────────────
    resultado = calcular_semaforo(hoy_ventas, promedio_30)
    resultado.update({
        "fuente": fuente,
        "fecha": hoy_str,
        "hora_consulta": datetime.now().strftime("%H:%M:%S"),
        "num_facturas_hoy": num_facturas_hoy if "num_facturas_hoy" in dir() else 0,
        "top_clientes": top_clientes,
        "historico_7dias": historico_7dias,
        "umbrales": {"verde": 90, "amarillo": 70},
    })

    return resultado


@router.get("/api/historico")
async def get_historico_ventas(
    dias: int = 30,
    db_ext: Session = Depends(get_external_db),
    user: User = Depends(get_current_active_user)
):
    """Histórico de ventas para gráfico de tendencia."""
    try:
        result = db_ext.execute(text("""
            SELECT CAST(fe_emis AS DATE) as dia,
                   ISNULL(SUM(monto_tot), 0) as total,
                   COUNT(DISTINCT doc_num) as num_facturas
            FROM saFacturaVenta
            WHERE fe_emis >= DATEADD(day, :neg_dias, GETDATE()) AND anulado = 0
            GROUP BY CAST(fe_emis AS DATE)
            ORDER BY dia ASC
        """), {"neg_dias": -abs(dias)}).fetchall()

        return [
            {"dia": str(r.dia), "total": float(r.total), "num_facturas": int(r.num_facturas)}
            for r in result
        ]
    except Exception as e:
        return []
