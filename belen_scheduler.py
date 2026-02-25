#!/usr/bin/env python3
"""
BELÉN Scheduler — Tareas programadas con IA
Envía reportes automáticos por Telegram a horas definidas.
Conecta con:
  - BELÉN (Ollama API) para generar análisis con IA
  - PostgreSQL (production-report DB) para consultar datos reales
  - Telegram Bot API para envío de mensajes

Instalación:
  pip install apscheduler python-telegram-bot sqlalchemy psycopg2-binary requests python-dotenv

Configuración:
  En el servidor, agrega al .env:
    TELEGRAM_BOT_TOKEN=<token de @BotFather>
    TELEGRAM_CHAT_ID=<ID del chat o grupo destino>
    OLLAMA_URL=http://localhost:11434
    BELEN_MODEL=belen_fast
"""

import os
import json
import logging
import requests
from datetime import datetime, date
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import sqlalchemy as sa
import urllib.parse

load_dotenv()

# ── Configuración ────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
BELEN_MODEL = os.getenv("BELEN_MODEL", "belen_fast")
DATABASE_URL = os.getenv("DATABASE_URL", "")

# SQL Server — Profit Plus (carmal_a)
SQLSRV_HOST = os.getenv("SQLSRV_HOST", "192.168.1.205")
SQLSRV_DB   = os.getenv("SQLSRV_DB",   "carmal_a")
SQLSRV_USER = os.getenv("SQLSRV_USER", "PROFIT")
SQLSRV_PASS = os.getenv("SQLSRV_PASS", "profit")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/home/administrador/belen_scheduler.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("BELEN-Scheduler")

# ── Utilidades ───────────────────────────────────────────────────

def send_telegram(message: str, parse_mode: str = "Markdown") -> bool:
    """Envía un mensaje por Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("Telegram no configurado. Defina TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID")
        print("📨 [SIN TELEGRAM] Mensaje que se enviaría:")
        print(message)
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": parse_mode
        }, timeout=10)
        if r.ok:
            log.info(f"Telegram ✅ enviado ({len(message)} chars)")
            return True
        else:
            log.error(f"Telegram error: {r.text}")
            return False
    except Exception as e:
        log.error(f"Error enviando Telegram: {e}")
        return False


def ask_belen(prompt: str, model: str = None) -> str:
    """Consulta a BELÉN (Ollama) y retorna la respuesta."""
    model = model or BELEN_MODEL
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 300}
            },
            timeout=120
        )
        if r.ok:
            return r.json().get("message", {}).get("content", "Sin respuesta")
        return f"Error Ollama: {r.status_code}"
    except Exception as e:
        return f"Error conectando a BELÉN: {e}"


def get_db_data(query: str) -> list:
    """Ejecuta una consulta en la base de datos y retorna filas."""
    if not DATABASE_URL:
        log.warning("DATABASE_URL no configurado")
        return []
    try:
        engine = sa.create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(sa.text(query))
            return [dict(row._mapping) for row in result]
    except Exception as e:
        log.error(f"Error DB: {e}")
        return []


def escape_md(text: str) -> str:
    """Escapa caracteres especiales para Telegram Markdown."""
    for char in ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
        text = text.replace(char, f'\\{char}')
    return text


# ── TAREAS PROGRAMADAS ───────────────────────────────────────────

def tarea_stock_bajo_minimo():
    """
    TAREA 1: Artículos con stock bajo mínimo
    Horario: Lunes-Viernes 8:00 AM
    """
    log.info("▶ Ejecutando: stock bajo mínimo")
    hoy = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Intentar consulta a la base de datos
    filas = get_db_data("""
        SELECT 
            co_art, art_des,
            CAST(stock_act AS INTEGER) as stock_actual,
            CAST(stock_min AS INTEGER) as stock_minimo
        FROM logistics_inventory
        WHERE stock_act IS NOT NULL AND stock_min IS NOT NULL
          AND CAST(stock_act AS FLOAT) < CAST(stock_min AS FLOAT)
        ORDER BY (CAST(stock_min AS FLOAT) - CAST(stock_act AS FLOAT)) DESC
        LIMIT 10
    """)

    if filas:
        lineas = "\n".join([
            f"• `{f['co_art']}` {f['art_des']}: *{f['stock_actual']}* (mín: {f['stock_minimo']})"
            for f in filas[:10]
        ])
        belen_analysis = ask_belen(
            f"Hay {len(filas)} artículos bajo stock mínimo. Los más críticos son: "
            f"{', '.join([f['art_des'] for f in filas[:3]])}. "
            f"Dame una recomendación de acción en 2 oraciones máximo."
        )
        mensaje = (
            f"📦 *ALERTA: STOCK BAJO MÍNIMO* — {hoy}\n\n"
            f"{lineas}\n\n"
            f"🤖 *BELÉN dice:*\n{belen_analysis}"
        )
    else:
        mensaje = (
            f"📦 *REPORTE STOCK* — {hoy}\n\n"
            f"✅ Todos los artículos están sobre el mínimo, o no hay datos configurados en la DB."
        )

    send_telegram(mensaje)


def tarea_resumen_produccion():
    """
    TAREA 2: Resumen de órdenes de producción del día
    Horario: Lunes-Viernes 7:00 AM
    """
    log.info("▶ Ejecutando: resumen producción")
    hoy = datetime.now().strftime("%d/%m/%Y")

    # Consultar órdenes de producción (tabla del production-report)
    filas = get_db_data("""
        SELECT 
            estado,
            COUNT(*) as cantidad,
            SUM(CAST(cantidad_planificada AS FLOAT)) as total_planificado,
            SUM(CAST(cantidad_producida AS FLOAT)) as total_producido
        FROM production_planning
        WHERE fecha >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY estado
        ORDER BY cantidad DESC
    """)

    analisis = ask_belen(
        f"Resumen de producción semana actual: {json.dumps(filas, default=str, ensure_ascii=False)}. "
        f"Dame un análisis ejecutivo de 3 líneas sobre el estado de producción."
    )

    if filas:
        lineas = "\n".join([
            f"• *{f.get('estado','?')}*: {f.get('cantidad',0)} órdenes"
            for f in filas
        ])
        mensaje = (
            f"🏭 *PRODUCCIÓN SEMANAL* — {hoy}\n\n"
            f"{lineas}\n\n"
            f"🤖 *Análisis BELÉN:*\n{analisis}"
        )
    else:
        mensaje = (
            f"🏭 *PRODUCCIÓN* — {hoy}\n\n"
            f"📊 Sin datos de producción en los últimos 7 días.\n\n"
            f"🤖 {analisis}"
        )

    send_telegram(mensaje)


def tarea_reporte_despachos():
    """
    TAREA 3: Despachos del día
    Horario: Lunes-Viernes 6:00 PM
    """
    log.info("▶ Ejecutando: reporte despachos del día")
    hoy = datetime.now().strftime("%d/%m/%Y")

    filas = get_db_data("""
        SELECT 
            COUNT(*) as total_despachos,
            SUM(CASE WHEN estado = 'completado' THEN 1 ELSE 0 END) as completados,
            SUM(CASE WHEN estado = 'pendiente' THEN 1 ELSE 0 END) as pendientes,
            SUM(CASE WHEN estado = 'cancelado' THEN 1 ELSE 0 END) as cancelados
        FROM logistics_dispatch
        WHERE DATE(fecha_despacho) = CURRENT_DATE
    """)

    datos = filas[0] if filas else {}
    total = datos.get('total_despachos', 0)
    completados = datos.get('completados', 0)
    pendientes = datos.get('pendientes', 0)

    analisis = ask_belen(
        f"Hoy hay {total} despachos: {completados} completados, {pendientes} pendientes. "
        f"¿Qué acciones sugiero para los pendientes? Responde en 2 oraciones."
    )

    mensaje = (
        f"🚚 *DESPACHOS DEL DÍA* — {hoy}\n\n"
        f"📊 Total: *{total}*\n"
        f"✅ Completados: *{completados}*\n"
        f"⏳ Pendientes: *{pendientes}*\n"
        f"❌ Cancelados: *{datos.get('cancelados', 0)}*\n\n"
        f"🤖 *BELÉN:* {analisis}"
    )
    send_telegram(mensaje)


def tarea_alerta_sin_movimiento():
    """
    TAREA 4: Artículos sin movimiento en 30 días (slow movers)
    Horario: Lunes 9:00 AM
    """
    log.info("▶ Ejecutando: artículos sin movimiento")
    hoy = datetime.now().strftime("%d/%m/%Y")

    filas = get_db_to_data("""
        SELECT 
            co_art, descripcion,
            CAST(cantidad AS INTEGER) as stock,
            ultima_actualizacion
        FROM logistics_inventory
        WHERE ultima_actualizacion < CURRENT_DATE - INTERVAL '30 days'
          AND CAST(cantidad AS FLOAT) > 0
        ORDER BY ultima_actualizacion ASC
        LIMIT 5
    """)

    if filas:
        lineas = "\n".join([
            f"• `{f.get('co_art', '?')}` {f.get('descripcion', '?')}: {f.get('stock', 0)} uds"
            for f in filas
        ])
        analisis = ask_belen(
            f"Hay {len(filas)} artículos con stock > 0 pero sin movimiento en 30+ días. "
            f"¿Qué estrategias recomiendas para liquidar inventario dormido? 3 sugerencias concretas."
        )
        mensaje = (
            f"😴 *INVENTARIO SIN MOVIMIENTO (+30 días)* — {hoy}\n\n"
            f"{lineas}\n\n"
            f"🤖 *Recomendaciones BELÉN:*\n{analisis}"
        )
    else:
        mensaje = f"😴 *SLOW MOVERS* — {hoy}\n\n✅ No hay artículos sin movimiento en 30 días."

    send_telegram(mensaje)


def tarea_personalizada(nombre: str, prompt_belen: str, emoji: str = "📋"):
    """
    Ejecuta una tarea personalizada con IA.
    Se puede usar para cualquier consulta ad-hoc a BELÉN.
    """
    log.info(f"▶ Ejecutando tarea personalizada: {nombre}")
    hoy = datetime.now().strftime("%d/%m/%Y %H:%M")

    respuesta = ask_belen(prompt_belen)
    mensaje = (
        f"{emoji} *{nombre.upper()}* — {hoy}\n\n"
        f"🤖 *BELÉN:*\n{respuesta}"
    )
    send_telegram(mensaje)


# ── CONFIGURACIÓN DEL SCHEDULER ──────────────────────────────────

def configurar_scheduler():
    """Define todas las tareas programadas."""
    scheduler = BlockingScheduler(timezone="America/Caracas")

    # ── TAREA 1: Stock bajo mínimo — Lunes a Viernes 8:00 AM
    scheduler.add_job(
        tarea_stock_bajo_minimo,
        CronTrigger(day_of_week="mon-fri", hour=8, minute=0),
        id="stock_bajo_minimo",
        name="Stock bajo mínimo",
        replace_existing=True
    )

    # ── TAREA 2: Resumen de producción — Lunes a Viernes 7:00 AM
    scheduler.add_job(
        tarea_resumen_produccion,
        CronTrigger(day_of_week="mon-fri", hour=7, minute=0),
        id="resumen_produccion",
        name="Resumen producción",
        replace_existing=True
    )

    # ── TAREA 3: Reporte de despachos — Lunes a Viernes 6:00 PM
    scheduler.add_job(
        tarea_reporte_despachos,
        CronTrigger(day_of_week="mon-fri", hour=18, minute=0),
        id="reporte_despachos",
        name="Reporte despachos del día",
        replace_existing=True
    )

    # ── TAREA 4: Artículos sin movimiento — Lunes 9:00 AM
    scheduler.add_job(
        tarea_alerta_sin_movimiento,
        CronTrigger(day_of_week="mon", hour=9, minute=0),
        id="sin_movimiento",
        name="Inventario sin movimiento",
        replace_existing=True
    )

    # ── TAREA 5: Análisis MP vs Compras — Lunes a Viernes 8:30 AM
    scheduler.add_job(
        tarea_analisis_mp_compras,
        CronTrigger(day_of_week="mon-fri", hour=8, minute=30),
        id="analisis_mp_compras",
        name="Análisis MP vs Compras",
        replace_existing=True
    )

    # ── TAREA 6: Buenos días + tip de BELÉN — Lunes a Viernes 7:30 AM
    scheduler.add_job(
        lambda: tarea_personalizada(
            "Buenos días",
            "Da un tip de gestión de inventarios o manufactura en español. "
            "Breve, práctico, aplicable hoy mismo. Máximo 3 oraciones.",
            "🌅"
        ),
        CronTrigger(day_of_week="mon-fri", hour=7, minute=30),
        id="buenos_dias",
        name="Buenos días + tip",
        replace_existing=True
    )

    return scheduler


# ── PUNTO DE ENTRADA ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("  🤖 BELÉN Scheduler — Iniciando")
    print(f"  Modelo: {BELEN_MODEL} @ {OLLAMA_URL}")
    print(f"  Telegram: {'✅ configurado' if TELEGRAM_TOKEN else '⚠️ NO configurado'}")
    print("=" * 60)

    # Modo test: ejecutar una tarea ahora mismo
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        tarea = sys.argv[2] if len(sys.argv) > 2 else "stock"
        print(f"\n🧪 Ejecutando test: {tarea}")
        if tarea == "stock":
            tarea_stock_bajo_minimo()
        elif tarea == "produccion":
            tarea_resumen_produccion()
        elif tarea == "despachos":
            tarea_reporte_despachos()
        elif tarea == "belen":
            prompt = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else "¿Qué es el análisis ABC de inventarios?"
            print(f"🤖 BELÉN: {ask_belen(prompt)}")
        else:
            print(f"Tareas disponibles: stock, produccion, despachos, belen '<pregunta>'")
        sys.exit(0)

    # Modo monitor: mostrar próximas tareas
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        scheduler = configurar_scheduler()
        print("\n📅 Tareas programadas:")
        for job in scheduler.get_jobs():
            print(f"  • {job.name} → próx: {job.next_run_time}")
        sys.exit(0)

    # Modo normal: iniciar scheduler
    scheduler = configurar_scheduler()
    print("\n📅 Tareas activas:")
    for job in scheduler.get_jobs():
        print(f"  • {job.name}")

    print(f"\n✅ Scheduler iniciado. Zona horaria: America/Caracas")
    print("   Para detener: Ctrl+C\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n⏹ Scheduler detenido.")
