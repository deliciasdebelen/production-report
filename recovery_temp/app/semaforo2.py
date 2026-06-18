# app/routers/semaforo2.py
# Semáforo 2 — Dashboard de Ventas Avanzado
# Datos: saFacturaVenta + saFacturaVentaReng + saArticulo + saVendedor + saCliente

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, date, timedelta
from typing import Optional

from ..dependencies import get_db, templates, get_current_user, get_current_active_user
from ..external_db import get_external_db
from ..models import User

router = APIRouter(prefix="/semaforo2", tags=["semaforo2"])


# ── Vista principal ───────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def semaforo2_view(request: Request, user: User = Depends(get_current_user)):
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("semaforo2.html", {
        "request": request, "user": user, "title": "Semáforo de Ventas v2"
    })


# ── Filtros de lookup ────────────────────────────────────────────

@router.get("/api/vendedores")
async def get_vendedores(db: Session = Depends(get_external_db), user: User = Depends(get_current_active_user)):
    try:
        r = db.execute(text("SELECT co_ven, ven_des FROM saVendedor WHERE inactivo=0 ORDER BY ven_des")).fetchall()
        return [{"co_ven": x.co_ven.strip(), "ven_des": x.ven_des.strip()} for x in r]
    except:
        return []


@router.get("/api/metas")
async def get_metas(db: Session = Depends(get_external_db), user: User = Depends(get_current_active_user)):
    """Intenta obtener metas desde Carmal; retorna estructura para configurar manualmente."""
    # Carmal no siempre tiene tabla de metas; retornamos estructura vacía si no existe
    try:
        r = db.execute(text("""
            SELECT co_ven, ISNULL(meta_cajas, 0) as cajas, ISNULL(meta_kg, 0) as kilos
            FROM saVendedorMeta
            ORDER BY co_ven
        """)).fetchall()
        return [dict(x._mapping) for x in r]
    except:
        return []


# ── API principal del dashboard ───────────────────────────────────

@router.get("/api/dashboard")
async def get_dashboard(
    fecha_ini: str = Query(default=None),
    fecha_fin: str = Query(default=None),
    vendedor: str = Query(default=""),
    tipo_venta: str = Query(default=""),      # "consignacion" | "venta_firme" | ""
    tipo_valor: str = Query(default="cajas"),  # "cajas" | "kilos" | "toneladas" | "unidades"
    meta: float = Query(default=0),
    db: Session = Depends(get_external_db),
    user: User = Depends(get_current_active_user)
):
    # Defaults de fecha: mes actual
    hoy = date.today()
    if not fecha_ini:
        fecha_ini = hoy.replace(day=1).isoformat()
    if not fecha_fin:
        fecha_fin = hoy.isoformat()

    fi = fecha_ini
    ff = fecha_fin
    dias_periodo = (date.fromisoformat(ff) - date.fromisoformat(fi)).days + 1

    # Filtro vendedor
    ven_filter = "AND f.co_ven = :ven" if vendedor else ""
    ven_params = {"ven": vendedor} if vendedor else {}

    # Filtro tipo de venta (consignación = tip_ven C, venta firme = V o F)
    tipo_filter = ""
    if tipo_venta == "consignacion":
        tipo_filter = "AND f.tip_ven = 'C'"
    elif tipo_venta == "venta_firme":
        tipo_filter = "AND (f.tip_ven = 'V' OR f.tip_ven IS NULL OR f.tip_ven != 'C')"

    # Columna de valor según tipo
    col_valor = {
        "cajas": "r.cant_cajas",
        "kilos": "r.peso_neto",
        "toneladas": "r.peso_neto / 1000.0",
        "unidades": "r.cant_und"
    }.get(tipo_valor, "r.cant_cajas")

    params = {"fi": fi, "ff": ff, **ven_params}

    result = {
        "kpis": {},
        "por_marca": [],
        "por_canal": [],
        "por_tipo_pedido": [],
        "diario": [],
        "stats": {}
    }

    try:
        # ── KPIs principales ──────────────────────────────────────
        kpi_sql = text(f"""
            SELECT
                ISNULL(SUM(f.monto_tot), 0) AS facturado_usd,
                COUNT(DISTINCT f.doc_num) AS num_facturas,
                COUNT(DISTINCT CAST(f.fe_emis AS DATE)) AS dias_con_fact
            FROM saFacturaVenta f
            WHERE f.fe_emis BETWEEN :fi AND :ff
              AND f.anulado = 0
              {ven_filter} {tipo_filter}
        """)
        kpi = db.execute(kpi_sql, params).fetchone()

        # Devoluciones
        dev_sql = text(f"""
            SELECT ISNULL(SUM(n.monto_tot), 0) AS total_dev
            FROM saNotaCreditoVenta n
            WHERE n.fe_emis BETWEEN :fi AND :ff AND n.anulado = 0
            {ven_filter.replace('f.co_ven', 'n.co_ven')}
        """)
        dev = db.execute(dev_sql, params).fetchone()

        # Pedidos pendientes
        ped_sql = text(f"""
            SELECT ISNULL(SUM(p.monto_tot), 0) AS pedidos_usd
            FROM saPedidoVenta p
            WHERE p.status != 'C' AND p.anulado = 0
            {ven_filter.replace('f.co_ven', 'p.co_ven')}
        """)
        ped = db.execute(ped_sql, {"ven": vendedor} if vendedor else {}).fetchone()

        fac_usd = float(kpi.facturado_usd) if kpi else 0
        dev_usd = float(dev.total_dev) if dev else 0
        ped_usd = float(ped.pedidos_usd) if ped else 0
        fac_neto = fac_usd - dev_usd
        cumplimiento = (fac_neto / meta * 100) if meta > 0 else 0
        dias_activos = int(kpi.dias_con_fact) if kpi else 0
        promedio_cal = fac_neto / dias_periodo if dias_periodo > 0 else 0
        promedio_act = fac_neto / dias_activos if dias_activos > 0 else 0
        proyectado = promedio_act * dias_periodo if promedio_act > 0 else 0
        cumplimiento_proy = (proyectado / meta * 100) if meta > 0 else 0

        result["kpis"] = {
            "meta": meta,
            "facturado_usd": round(fac_usd, 2),
            "devolucion_usd": round(dev_usd, 2),
            "pedidos_usd": round(ped_usd, 2),
            "facturado_neto": round(fac_neto, 2),
            "facturado_mas_pedidos": round(fac_neto + ped_usd, 2),
            "cumplimiento_pct": round(cumplimiento, 2),
            "cumplimiento_proyectado_pct": round(cumplimiento_proy, 2),
        }

        result["stats"] = {
            "dias_periodo": dias_periodo,
            "dias_con_facturacion": dias_activos,
            "promedio_dia_calendario": round(promedio_cal, 2),
            "promedio_dia_activos": round(promedio_act, 2),
            "num_facturas": int(kpi.num_facturas) if kpi else 0,
            "promedio_fact_diaria": round(fac_neto / dias_activos if dias_activos > 0 else 0, 2),
        }

        # ── Resumen por Marca (saLineaArticulo) ──────────────────
        marca_sql = text(f"""
            SELECT
                ISNULL(l.lin_des, 'SIN MARCA') AS marca,
                ISNULL(SUM({col_valor}), 0) AS valor
            FROM saFacturaVenta f
            JOIN saFacturaVentaReng r ON f.doc_num = r.doc_num
            JOIN saArticulo a ON r.co_art = a.co_art
            LEFT JOIN saLineaArticulo l ON a.co_lin = l.co_lin
            WHERE f.fe_emis BETWEEN :fi AND :ff AND f.anulado = 0
              {ven_filter} {tipo_filter}
            GROUP BY l.lin_des
            ORDER BY valor DESC
        """)
        marcas = db.execute(marca_sql, params).fetchall()
        result["por_marca"] = [
            {"marca": m.marca.strip() if m.marca else "Sin Marca", "valor": round(float(m.valor), 2)}
            for m in marcas
        ]

        # ── Corporativo vs Fuerza de Ventas ───────────────────────
        canal_sql = text(f"""
            SELECT
                CASE WHEN c.tipo_cli = 'C' THEN 'CORPORATIVO'
                     ELSE 'FUERZA DE VENTAS' END AS canal,
                ISNULL(SUM({col_valor}), 0) AS valor,
                ISNULL(SUM(f.monto_tot), 0) AS monto,
                COUNT(DISTINCT f.doc_num) AS facturas
            FROM saFacturaVenta f
            JOIN saFacturaVentaReng r ON f.doc_num = r.doc_num
            LEFT JOIN saCliente c ON f.co_cli = c.co_cli
            WHERE f.fe_emis BETWEEN :fi AND :ff AND f.anulado = 0
              {ven_filter} {tipo_filter}
            GROUP BY CASE WHEN c.tipo_cli = 'C' THEN 'CORPORATIVO' ELSE 'FUERZA DE VENTAS' END
        """)
        canales = db.execute(canal_sql, params).fetchall()
        total_canal = sum(float(c.valor) for c in canales) or 1
        result["por_canal"] = [
            {
                "canal": c.canal,
                "valor": round(float(c.valor), 2),
                "pct": round(float(c.valor) / total_canal * 100, 1)
            }
            for c in canales
        ]

        # ── Pedidos por tipo (Consignación vs Venta Firme) ────────
        tipo_sql = text("""
            SELECT
                CASE WHEN p.tip_ven = 'C' THEN 'CONSIGNACIÓN' ELSE 'VENTA FIRME' END AS tipo,
                COUNT(DISTINCT p.doc_num) AS pedidos,
                ISNULL(SUM(p.monto_tot), 0) AS monto
            FROM saPedidoVenta p
            WHERE p.status != 'C' AND p.anulado = 0
            GROUP BY CASE WHEN p.tip_ven = 'C' THEN 'CONSIGNACIÓN' ELSE 'VENTA FIRME' END
        """)
        tipos = db.execute(tipo_sql, {}).fetchall()
        total_tipos = sum(int(t.pedidos) for t in tipos) or 1
        result["por_tipo_pedido"] = [
            {
                "tipo": t.tipo,
                "pedidos": int(t.pedidos),
                "monto": round(float(t.monto), 2),
                "pct": round(int(t.pedidos) / total_tipos * 100, 1)
            }
            for t in tipos
        ]

        # ── Resumen diario ────────────────────────────────────────
        diario_sql = text(f"""
            SELECT
                CAST(f.fe_emis AS DATE) AS dia,
                ISNULL(SUM(f.monto_tot), 0) AS facturado,
                COUNT(DISTINCT f.doc_num) AS facturas
            FROM saFacturaVenta f
            WHERE f.fe_emis BETWEEN :fi AND :ff AND f.anulado = 0
              {ven_filter} {tipo_filter}
            GROUP BY CAST(f.fe_emis AS DATE)
            ORDER BY dia
        """)
        # Pedidos pendientes diarios
        ped_diario_sql = text(f"""
            SELECT
                CAST(p.fe_emis AS DATE) AS dia,
                COUNT(DISTINCT p.doc_num) AS pedidos
            FROM saPedidoVenta p
            WHERE p.fe_emis BETWEEN :fi AND :ff AND p.anulado = 0 AND p.status != 'C'
            GROUP BY CAST(p.fe_emis AS DATE)
            ORDER BY dia
        """)
        diario = db.execute(diario_sql, params).fetchall()
        ped_diario = db.execute(ped_diario_sql, params).fetchall()
        ped_map = {str(p.dia): int(p.pedidos) for p in ped_diario}

        result["diario"] = [
            {
                "dia": str(d.dia),
                "facturado": round(float(d.facturado), 2),
                "facturas": int(d.facturas),
                "pedidos_pendientes": ped_map.get(str(d.dia), 0)
            }
            for d in diario
        ]

    except Exception as e:
        result["error"] = str(e)
        # Datos demo si Carmal no responde
        result["kpis"] = {
            "meta": meta, "facturado_usd": 0, "devolucion_usd": 0,
            "pedidos_usd": 0, "facturado_neto": 0, "facturado_mas_pedidos": 0,
            "cumplimiento_pct": 0, "cumplimiento_proyectado_pct": 0
        }
        result["stats"] = {
            "dias_periodo": dias_periodo, "dias_con_facturacion": 0,
            "promedio_dia_calendario": 0, "promedio_dia_activos": 0,
            "num_facturas": 0, "promedio_fact_diaria": 0
        }

    result["meta"] = {"fecha_ini": fi, "fecha_fin": ff, "tipo_valor": tipo_valor}
    return result
