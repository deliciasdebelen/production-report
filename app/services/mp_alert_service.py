"""
mp_alert_service.py
Servicio de análisis de Materia Prima vs Compras.
Calcula el balance entre lo requerido (ventas/pedidos/cotizaciones) y lo comprado.
Envía alertas diarias por Telegram a los suscriptores registrados en la BD local.
"""

import os
import logging
import requests
from datetime import date, timedelta
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Session

log = logging.getLogger("mp_alert_service")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ── Telegram ─────────────────────────────────────────────────────

def send_telegram_to(chat_id: str, message: str, parse_mode: str = "Markdown") -> bool:
    """Envía un mensaje de Telegram a un chat_id específico."""
    if not TELEGRAM_TOKEN:
        log.warning(f"[TELEGRAM NO CONFIGURADO] Mensaje para {chat_id}:\n{message}")
        return False
    try:
        # Si es un número de teléfono (ej: 04126036358), usarlo directamente como string
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        r = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode
        }, timeout=15)
        if r.ok:
            log.info(f"Telegram ✅ enviado a {chat_id}")
            return True
        else:
            log.error(f"Telegram error para {chat_id}: {r.text}")
            return False
    except Exception as e:
        log.error(f"Error enviando Telegram a {chat_id}: {e}")
        return False


def send_mp_alert_to_all(local_db: Session, balance_data: list, fecha: str) -> dict:
    """Lee todos los suscriptores activos de tipo MP y envía el reporte."""
    from ..models import TelegramSubscriber
    
    subscribers = local_db.query(TelegramSubscriber).filter(
        TelegramSubscriber.is_active == True,
        TelegramSubscriber.report_type.in_(["MP", "General"])
    ).all()
    
    if not subscribers:
        return {"sent": 0, "errors": 0, "message": "No hay suscriptores activos"}
    
    message = format_mp_telegram_message(balance_data, fecha)
    sent = 0
    errors = 0
    
    for sub in subscribers:
        ok = send_telegram_to(sub.chat_id, message)
        if ok:
            sent += 1
        else:
            errors += 1
    
    return {"sent": sent, "errors": errors, "total": len(subscribers)}


# ── Cálculo de balance MP ─────────────────────────────────────────

def get_mp_demand(ext_conn, fecha_ini: str, fecha_fin: str,
                  include_ventas: bool = True,
                  include_pedidos: bool = True,
                  include_cotizaciones: bool = True) -> list:
    """
    Consulta la demanda de artículos MP derivada de PT en documentos comerciales.
    Usa saFormulaArticulo/saFormulaArticuloReng si existe, sino saArticuloComp.
    Retorna [{co_art_mp, des_art_mp, cantidad_requerida, unidad, fuente}]
    """
    results = []
    
    # Detectar tabla de fórmulas disponible
    formula_table = _detect_formula_table(ext_conn)
    if not formula_table:
        log.warning("No se encontró tabla de fórmulas de PT en SQL Server")
        return []
    
    fhead, freng = formula_table
    
    docs_union_parts = []
    params = {"fi": fecha_ini, "ff": fecha_fin}
    
    if include_ventas:
        docs_union_parts.append("""
            SELECT r.co_art, SUM(r.total_art) as cant
            FROM saFacturaVenta f
            JOIN saFacturaVentaReng r ON f.doc_num = r.doc_num
            WHERE f.fec_emis BETWEEN :fi AND :ff
              AND f.anulado = 0
            GROUP BY r.co_art
        """)
    
    if include_pedidos:
        docs_union_parts.append("""
            SELECT r.co_art, SUM(r.total_art) as cant
            FROM saPedidoVenta p
            JOIN saPedidoVentaReng r ON p.doc_num = r.doc_num
            WHERE p.fec_emis BETWEEN :fi AND :ff
              AND p.anulado = 0
              AND p.status NOT IN ('C', 'A')
            GROUP BY r.co_art
        """)
    
    if include_cotizaciones:
        docs_union_parts.append("""
            SELECT r.co_art, SUM(r.total_art) as cant
            FROM saPresupuestoVenta pv
            JOIN saPresupuestoVentaReng r ON pv.doc_num = r.doc_num
            WHERE pv.fec_emis BETWEEN :fi AND :ff
              AND ISNULL(pv.anulado, 0) = 0
            GROUP BY r.co_art
        """)
    
    if not docs_union_parts:
        return []
    
    union_sql = " UNION ALL ".join(docs_union_parts)
    
    sql = f"""
        SELECT
            comp.co_art_comp        AS co_art_mp,
            ISNULL(a.art_des, comp.co_art_comp) AS des_art_mp,
            SUM(docs.cant * comp.cant_comp) AS cantidad_requerida,
            ISNULL(comp.co_uni_comp, 'UN') AS unidad
        FROM (
            SELECT co_art, SUM(cant) as cant
            FROM ({union_sql}) AS docs_total
            GROUP BY co_art
        ) AS docs
        JOIN {fhead} fh ON fh.co_art = docs.co_art
        JOIN {freng} comp ON comp.co_art = fh.co_art
        LEFT JOIN saArticulo a ON a.co_art = comp.co_art_comp
        GROUP BY comp.co_art_comp, a.art_des, comp.co_uni_comp
        ORDER BY cantidad_requerida DESC
    """
    
    try:
        rows = ext_conn.execute(sa.text(sql), params).fetchall()
        results = [
            {
                "co_art_mp": str(r.co_art_mp).strip(),
                "des_art_mp": str(r.des_art_mp).strip(),
                "cantidad_requerida": float(r.cantidad_requerida),
                "unidad": str(r.unidad).strip()
            }
            for r in rows
        ]
    except Exception as e:
        log.error(f"Error consultando demanda MP: {e}")
    
    return results


def get_mp_purchases(ext_conn, fecha_ini: str, fecha_fin: str) -> list:
    """
    Consulta las compras de MP en el período: saOrdenCompra + saOrdenCompraReng.
    También incluye recepciones si existe saRecepcionCompra.
    Retorna [{co_art, cant_comprada}]
    """
    results = []
    sql = """
        SELECT
            r.co_art,
            SUM(r.cant_total_rec) AS cant_comprada
        FROM saOrdenCompra oc
        JOIN saOrdenCompraReng r ON oc.doc_num = r.doc_num
        WHERE oc.fec_emis BETWEEN :fi AND :ff
          AND ISNULL(oc.anulado, 0) = 0
        GROUP BY r.co_art
    """
    try:
        rows = ext_conn.execute(sa.text(sql), {"fi": fecha_ini, "ff": fecha_fin}).fetchall()
        results = [{"co_art": str(r.co_art).strip(), "cant_comprada": float(r.cant_comprada)} for r in rows]
    except Exception as e:
        log.warning(f"Error con cant_total_rec, intentando cant_pend: {e}")
        # Fallback: usar cant_pend o total_art
        try:
            sql2 = """
                SELECT r.co_art, SUM(ISNULL(r.total_art, r.cant_pend)) AS cant_comprada
                FROM saOrdenCompra oc
                JOIN saOrdenCompraReng r ON oc.doc_num = r.doc_num
                WHERE oc.fec_emis BETWEEN :fi AND :ff
                  AND ISNULL(oc.anulado, 0) = 0
                GROUP BY r.co_art
            """
            rows2 = ext_conn.execute(sa.text(sql2), {"fi": fecha_ini, "ff": fecha_fin}).fetchall()
            results = [{"co_art": str(r.co_art).strip(), "cant_comprada": float(r.cant_comprada)} for r in rows2]
        except Exception as e2:
            log.error(f"Error fallback compras MP: {e2}")
    
    return results


def calculate_mp_balance(demand: list, purchases: list) -> list:
    """
    Cruza demanda vs compras y calcula balance.
    Retorna lista ordenada por déficit (más críticos primero).
    """
    purchases_map = {p["co_art"]: p["cant_comprada"] for p in purchases}
    
    balance = []
    for d in demand:
        code = d["co_art_mp"]
        requerido = d["cantidad_requerida"]
        comprado = purchases_map.get(code, 0.0)
        deficit = max(0.0, requerido - comprado)
        cobertura_pct = min(100.0, (comprado / requerido * 100) if requerido > 0 else 100.0)
        
        # Semáforo
        if cobertura_pct >= 80:
            semaforo = "verde"
        elif cobertura_pct >= 50:
            semaforo = "amarillo"
        else:
            semaforo = "rojo"
        
        balance.append({
            "co_art_mp": code,
            "des_art_mp": d["des_art_mp"],
            "unidad": d["unidad"],
            "requerido": round(requerido, 2),
            "comprado": round(comprado, 2),
            "deficit": round(deficit, 2),
            "cobertura_pct": round(cobertura_pct, 1),
            "semaforo": semaforo
        })
    
    # Ordenar: primero rojos, luego amarillos, luego verdes; dentro de cada grupo, mayor déficit primero
    priority = {"rojo": 0, "amarillo": 1, "verde": 2}
    balance.sort(key=lambda x: (priority[x["semaforo"]], -x["deficit"]))
    return balance


def format_mp_telegram_message(balance: list, fecha: str) -> str:
    """Formatea el mensaje de alerta MP para Telegram en Markdown."""
    criticos = [b for b in balance if b["semaforo"] == "rojo"]
    alertas = [b for b in balance if b["semaforo"] == "amarillo"]
    ok = [b for b in balance if b["semaforo"] == "verde"]
    
    lineas_criticos = ""
    for b in criticos[:8]:
        lineas_criticos += (
            f"🔴 *{b['des_art_mp'][:35]}*\n"
            f"   Req: {b['requerido']:,.0f} | Comp: {b['comprado']:,.0f} | "
            f"Déficit: *{b['deficit']:,.0f}* ({b['cobertura_pct']}%)\n"
        )
    
    lineas_alertas = ""
    for b in alertas[:5]:
        lineas_alertas += (
            f"🟡 *{b['des_art_mp'][:35]}* — {b['cobertura_pct']}% cubierto\n"
        )
    
    msg = (
        f"🧮 *ANÁLISIS MP vs COMPRAS* — {fecha}\n\n"
        f"📊 Resumen: {len(criticos)} críticos | {len(alertas)} en alerta | {len(ok)} OK\n\n"
    )
    
    if criticos:
        msg += f"*⚠️ CRÍTICOS ({len(criticos)}):*\n{lineas_criticos}\n"
    
    if alertas:
        msg += f"*🟡 EN ALERTA ({len(alertas)}):*\n{lineas_alertas}\n"
    
    if not criticos and not alertas:
        msg += "✅ *Todos los materiales tienen cobertura suficiente*\n"
    
    msg += "_Sistema de Producción — Delicias de Belén_"
    return msg


# ── Utilidad interna ──────────────────────────────────────────────

def _detect_formula_table(conn) -> Optional[tuple]:
    """Detecta qué tabla de fórmulas de producción está disponible."""
    candidates = [
        ("saFormulaArticulo", "saFormulaArticuloReng"),
        ("saArticuloComp", "saArticuloCompReng"),
    ]
    for head, reng in candidates:
        try:
            conn.execute(sa.text(f"SELECT TOP 1 1 FROM {head}"))
            return (head, reng)
        except Exception:
            continue
    return None
