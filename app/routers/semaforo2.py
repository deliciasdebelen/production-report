# app/routers/semaforo2.py
# Semáforo 2 — Dashboard de Ventas Avanzado
# Campos verificados en DB Carmal (SQL Server 2014):
#   saFacturaVenta:     doc_num, fec_emis, co_cli, co_ven, co_mone, anulado, status, total_neto, total_bruto
#   saFacturaVentaReng: doc_num, reng_num, co_art, des_art, total_art, reng_neto
#   saTasa:             co_mone, fecha, tasa_c, tasa_v  ← tasa de cambio por fecha/moneda
#   saArticulo:         co_art, art_des, co_lin
#   saVendedor:         co_ven, ven_des, inactivo
#   saCliente:          co_cli, cli_des, tip_cli
#
# CONVERSIÓN: total_neto (Bs) / saTasa.tasa_v (del día, misma moneda de la factura) = USD

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date

from ..dependencies import get_db, templates, get_current_user, get_current_active_user
from ..external_db import get_external_db
from ..models import User

router = APIRouter(prefix="/semaforo2", tags=["semaforo2"])


# ── Vista principal ──────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def semaforo2_view(request: Request, user: User = Depends(get_current_user)):
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("semaforo2.html", {
        "request": request, "user": user, "title": "Semáforo de Ventas v2"
    })


# ── Vendedores lookup ────────────────────────────────────────────

@router.get("/api/vendedores")
async def get_vendedores(db: Session = Depends(get_external_db),
                         user: User = Depends(get_current_active_user)):
    try:
        r = db.execute(text(
            "SELECT co_ven, ven_des FROM saVendedor WHERE inactivo=0 ORDER BY ven_des"
        )).fetchall()
        return [{"co_ven": str(x.co_ven).strip(), "ven_des": str(x.ven_des).strip()} for x in r]
    except Exception:
        return []


# ── Tasas de cambio disponibles (últimas) ──────────────────────

@router.get("/api/tasas")
async def get_tasas(db: Session = Depends(get_external_db),
                    user: User = Depends(get_current_active_user)):
    """Devuelve las últimas tasas de cambio registradas en saTasa."""
    try:
        r = db.execute(text("""
            SELECT t.co_mone, m.mone_des, t.fecha, t.tasa_c, t.tasa_v
            FROM saTasa t
            JOIN saMoneda m ON t.co_mone = m.co_mone
            WHERE t.fecha = (SELECT MAX(fecha) FROM saTasa t2 WHERE t2.co_mone = t.co_mone)
            ORDER BY t.co_mone
        """)).fetchall()
        return [{"co_mone": x.co_mone.strip(), "mone_des": x.mone_des.strip(),
                 "fecha": str(x.fecha), "tasa_c": float(x.tasa_c),
                 "tasa_v": float(x.tasa_v)} for x in r]
    except Exception as e:
        return {"error": str(e)}


# ── Diagnóstico INFORMATION_SCHEMA ──────────────────────────────

@router.get("/api/debug/columnas")
async def debug_columnas(tabla: str = "saFacturaVenta",
                         db: Session = Depends(get_external_db),
                         user: User = Depends(get_current_active_user)):
    try:
        r = db.execute(text(
            "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = :t ORDER BY ORDINAL_POSITION"
        ), {"t": tabla}).fetchall()
        cols = [{"col": x.COLUMN_NAME, "tipo": x.DATA_TYPE} for x in r]
        return {"tabla": tabla, "columnas": cols, "total": len(cols)}
    except Exception as e:
        return {"tabla": tabla, "error": str(e)}


# ── API principal ────────────────────────────────────────────────

@router.get("/api/dashboard")
async def get_dashboard(
    fecha_ini: str = Query(default=None),
    fecha_fin: str = Query(default=None),
    vendedor:   str = Query(default=""),
    tipo_venta: str = Query(default=""),
    tipo_valor: str = Query(default="cajas"),
    meta: float     = Query(default=0),
    db: Session     = Depends(get_external_db),
    user: User      = Depends(get_current_active_user)
):
    hoy = date.today()
    if not fecha_ini:
        fecha_ini = hoy.replace(day=1).isoformat()
    if not fecha_fin:
        fecha_fin = hoy.isoformat()

    fi = fecha_ini
    ff = fecha_fin
    dias_periodo = (date.fromisoformat(ff) - date.fromisoformat(fi)).days + 1

    # Filtros SQL
    ven_f  = "AND f.co_ven = :ven" if vendedor else ""
    tipo_f = ""
    if tipo_venta == "consignacion":
        tipo_f = "AND f.tip_ven = 'C'"
    elif tipo_venta == "venta_firme":
        tipo_f = "AND (f.tip_ven != 'C' OR f.tip_ven IS NULL)"

    params = {"fi": fi, "ff": ff}
    if vendedor:
        params["ven"] = vendedor

    # ── JOIN de tasa de cambio por fecha y moneda ────────────────
    # saTasa.tasa_v = tasa de venta (Bs por 1 USD)
    # USD = total_neto_bs / tasa_v
    # Si la factura ya está en la moneda base (sin tasa), tasa_v = 1 y no divide nada.
    TASA_JOIN = """
        LEFT JOIN saTasa t ON CAST(f.fec_emis AS DATE) = CAST(t.fecha AS DATE)
                           AND t.co_mone = f.co_mone
    """
    # Expresión de monto convertido a USD
    USD_EXPR  = "f.total_neto / NULLIF(t.tasa_v, 0)"
    USD_EXPR_RENG = "r.reng_neto / NULLIF(t.tasa_v, 0)"

    errors = {}
    result = {
        "kpis": {
            "meta": meta, "facturado_usd": 0, "devolucion_usd": 0,
            "pedidos_usd": 0, "facturado_neto": 0, "facturado_mas_pedidos": 0,
            "cumplimiento_pct": 0, "cumplimiento_proyectado_pct": 0,
        },
        "por_marca": [], "por_canal": [], "por_tipo_pedido": [], "diario": [],
        "stats": {
            "dias_periodo": dias_periodo, "dias_con_facturacion": 0,
            "promedio_dia_calendario": 0, "promedio_dia_activos": 0,
            "num_facturas": 0, "promedio_fact_diaria": 0,
        },
        "errors": errors,
        "meta": {"fecha_ini": fi, "fecha_fin": ff, "tipo_valor": tipo_valor}
    }

    # ── 1. KPI Facturado (Bs → USD) ──────────────────────────────
    fac_usd = num_fact = dias_act = 0
    try:
        r = db.execute(text(f"""
            SELECT
                ISNULL(SUM({USD_EXPR}), 0)                            AS facturado_usd,
                COUNT(DISTINCT f.doc_num)                              AS num_facturas,
                COUNT(DISTINCT CAST(f.fec_emis AS DATE))               AS dias_con_fact
            FROM saFacturaVenta f
            {TASA_JOIN}
            WHERE f.fec_emis BETWEEN :fi AND :ff
              AND f.anulado = 0
              {ven_f} {tipo_f}
        """), params).fetchone()
        fac_usd  = float(r.facturado_usd) if r else 0
        num_fact = int(r.num_facturas)    if r else 0
        dias_act = int(r.dias_con_fact)   if r else 0
    except Exception as e:
        errors["kpi_facturado"] = str(e)

    # ── 2. Pedidos pendientes (tasa por fecha del pedido) ──────────
    ped_usd = 0
    try:
        ven_f_p = "AND p.co_ven = :ven" if vendedor else ""
        r3 = db.execute(text(f"""
            SELECT ISNULL(SUM(
                p.total_neto / NULLIF(tp.tasa_v, 0)
            ), 0) AS pedidos
            FROM saPedidoVenta p
            LEFT JOIN saTasa tp ON CAST(p.fec_emis AS DATE) = CAST(tp.fecha AS DATE)
                                AND tp.co_mone = p.co_mone
            WHERE p.status NOT IN ('C', 'A') AND p.anulado = 0
            {ven_f_p}
        """), params).fetchone()
        ped_usd = float(r3.pedidos) if r3 else 0
    except Exception as e:
        errors["pedidos"] = str(e)

    # ── Derivados ────────────────────────────────────────────────
    dev_usd     = 0
    fac_neto    = fac_usd - dev_usd
    fac_mas_ped = fac_neto + ped_usd
    cumpl       = (fac_neto / meta * 100) if meta > 0 else 0
    prom_cal    = fac_neto / dias_periodo if dias_periodo > 0 else 0
    prom_act    = fac_neto / dias_act     if dias_act > 0 else 0
    proy        = prom_act * dias_periodo if prom_act > 0 else 0
    cumpl_proy  = (proy / meta * 100)    if meta > 0 else 0

    result["kpis"] = {
        "meta":                        meta,
        "facturado_usd":               round(fac_usd,      2),
        "devolucion_usd":              round(dev_usd,       2),
        "pedidos_usd":                 round(ped_usd,       2),
        "facturado_neto":              round(fac_neto,      2),
        "facturado_mas_pedidos":       round(fac_mas_ped,   2),
        "cumplimiento_pct":            round(cumpl,         2),
        "cumplimiento_proyectado_pct": round(cumpl_proy,    2),
    }
    result["stats"] = {
        "dias_periodo":            dias_periodo,
        "dias_con_facturacion":    dias_act,
        "promedio_dia_calendario": round(prom_cal, 2),
        "promedio_dia_activos":    round(prom_act, 2),
        "num_facturas":            num_fact,
        "promedio_fact_diaria":    round(fac_neto / dias_act if dias_act > 0 else 0, 2),
    }

    # ── 3. Por Marca (reng_neto → USD usando tasa de la factura) ─
    try:
        r4 = db.execute(text(f"""
            SELECT
                ISNULL(a.co_lin, 'SIN MARCA') AS marca,
                ISNULL(SUM({USD_EXPR_RENG}), 0) AS valor
            FROM saFacturaVenta f
            JOIN saFacturaVentaReng r ON f.doc_num = r.doc_num
            JOIN saArticulo a          ON r.co_art  = a.co_art
            {TASA_JOIN}
            WHERE f.fec_emis BETWEEN :fi AND :ff AND f.anulado = 0
              {ven_f} {tipo_f}
            GROUP BY a.co_lin
            ORDER BY valor DESC
        """), params).fetchall()
        result["por_marca"] = [
            {"marca": str(x.marca).strip(), "valor": round(float(x.valor), 2)}
            for x in r4
        ]
    except Exception as e:
        errors["por_marca"] = str(e)

    # ── 4. Corporativo vs FDV (total_neto → USD) ─────────────────
    try:
        r5 = db.execute(text(f"""
            SELECT
                CASE WHEN c.tip_cli = 'C' THEN 'CORPORATIVO' ELSE 'FUERZA DE VENTAS' END AS canal,
                ISNULL(SUM({USD_EXPR}), 0) AS monto
            FROM saFacturaVenta f
            LEFT JOIN saCliente c ON f.co_cli = c.co_cli
            {TASA_JOIN}
            WHERE f.fec_emis BETWEEN :fi AND :ff AND f.anulado = 0
              {ven_f} {tipo_f}
            GROUP BY CASE WHEN c.tip_cli = 'C' THEN 'CORPORATIVO' ELSE 'FUERZA DE VENTAS' END
        """), params).fetchall()
        total_canal = sum(float(x.monto) for x in r5) or 1
        result["por_canal"] = [
            {"canal": x.canal, "valor": round(float(x.monto), 2),
             "pct": round(float(x.monto) / total_canal * 100, 1)}
            for x in r5
        ]
    except Exception as e:
        errors["por_canal"] = str(e)

    # ── 5. Pedidos por tipo (tasa por fecha del pedido) ─────────────
    try:
        r6 = db.execute(text("""
            SELECT
                'PEDIDOS PENDIENTES'              AS tipo,
                COUNT(DISTINCT p.doc_num)         AS pedidos,
                ISNULL(SUM(p.total_neto / NULLIF(tp.tasa_v, 0)), 0) AS monto
            FROM saPedidoVenta p
            LEFT JOIN saTasa tp ON CAST(p.fec_emis AS DATE) = CAST(tp.fecha AS DATE)
                                AND tp.co_mone = p.co_mone
            WHERE p.status NOT IN ('C', 'A') AND p.anulado = 0
        """)).fetchall()
        total_t = sum(int(x.pedidos) for x in r6) or 1
        result["por_tipo_pedido"] = [
            {"tipo": x.tipo, "pedidos": int(x.pedidos), "monto": round(float(x.monto), 2),
             "pct": round(int(x.pedidos) / total_t * 100, 1)}
            for x in r6
        ]
    except Exception as e:
        errors["por_tipo_pedido"] = str(e)

    # ── 6. Diario (total_neto → USD con tasa del día) ────────────
    try:
        r7 = db.execute(text(f"""
            SELECT
                CAST(f.fec_emis AS DATE)          AS dia,
                ISNULL(SUM({USD_EXPR}), 0)        AS facturado,
                COUNT(DISTINCT f.doc_num)          AS facturas
            FROM saFacturaVenta f
            {TASA_JOIN}
            WHERE f.fec_emis BETWEEN :fi AND :ff AND f.anulado = 0
              {ven_f} {tipo_f}
            GROUP BY CAST(f.fec_emis AS DATE)
            ORDER BY dia
        """), params).fetchall()
        result["diario"] = [
            {"dia": str(x.dia), "facturado": round(float(x.facturado), 2),
             "facturas": int(x.facturas), "pedidos_pendientes": 0}
            for x in r7
        ]
    except Exception as e:
        errors["diario"] = str(e)

    return result
