"""
BCV Tasa Service — Scraping automático de la tasa BCV y actualización en Profit (saTasa)

Lógica de negocio:
  - BCV publica la tasa del USD y EUR entre las 17:00 y 21:00 de cada día hábil.
  - La tasa publicada el DÍA D aplica en Profit para el DÍA D+1 (siguiente día hábil).
  - Este servicio raspa bcv.org.ve cada 5 min de 17:00 a 21:00 y, cuando encuentra la
    nueva tasa (distinta a la del día anterior), la inserta en saTasa para D+1.
  - Se actualiza tanto co_mone='USD' (ventas y compras en dólar BCV) como 'EUR' (euro BCV).
  - Lleva un rastro/log en memoria y en archivo persistente.

Servidor Profit: 192.168.60.15  BD: carmal_a  Tabla: saTasa
"""
import os
import re
import json
import logging
import traceback
import pyodbc
import requests
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Tuple
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── Conexión Profit (Cargada dinámicamente) ──────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bcv_config.json")

def load_bcv_config() -> dict:
    """Carga la configuración de la BD de saTasa desde bcv_config.json o .env fallback."""
    config = {
        "host": os.getenv("SQLSRV_HOST_CXC", "192.168.60.15"),
        "instance": "",
        "database": "carmal_a",
        "user": os.getenv("SQLSRV_USER_CXC", "sa"),
        "password": os.getenv("SQLSRV_PASS_CXC", ""),
        "port": ""
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
                config.update(saved)
        except Exception as e:
            logger.error(f"Error cargando config de Tasa BCV: {e}")
    return config

def save_bcv_config(config: dict) -> bool:
    """Guarda la configuración de la BD de saTasa en bcv_config.json."""
    try:
        cleaned = {
            "host": str(config.get("host", "192.168.60.15")).strip(),
            "instance": str(config.get("instance", "")).strip(),
            "database": str(config.get("database", "carmal_a")).strip(),
            "user": str(config.get("user", "sa")).strip(),
            "password": str(config.get("password", "")),
            "port": str(config.get("port", "")).strip()
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)
        _log("INFO", "Configuración de BD Profit para BCV actualizada.")
        return True
    except Exception as e:
        _log("ERROR", f"Error guardando config de Tasa BCV: {e}")
        return False

def test_profit_connection(cfg: dict = None) -> Tuple[bool, str]:
    """Prueba la conexión a Profit usando la config dada o la guardada."""
    if cfg is None:
        cfg = load_bcv_config()
    server = cfg["host"]
    if cfg.get("instance"):
        server = f"{server}\\{cfg['instance']}"
    if cfg.get("port"):
        server = f"{server},{cfg['port']}"
        
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={cfg['database']};"
        f"UID={cfg['user']};"
        f"PWD={cfg['password']};"
        "TrustServerCertificate=yes;Connection Timeout=10;"
    )
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        cur = conn.cursor()
        cur.execute("SELECT TOP 1 co_mone FROM saTasa")
        row = cur.fetchone()
        conn.close()
        return True, "Conexión exitosa a la tabla saTasa de Profit."
    except Exception as e:
        return False, str(e)


# ── Log persistente ──────────────────────────────────────────────────────────
LOG_FILE = "/tmp/bcv_tasa_rastro.json"
_rastro_memoria: List[dict] = []       # log en memoria (últimas 500 entradas)

# ── Monedas que actualiza ────────────────────────────────────────────────────
# Ventas y compras usan USD (Dólar BCV) y EUR (Euro BCV)
MONEDAS_BCV = {
    "USD": {"id_html": "dolar", "label": "Dólar BCV", "co_mone": "USD"},
    "EUR": {"id_html": "euro",  "label": "Euro BCV",  "co_mone": "EUR"},
}

# ── Usuarios Profit para auditoría ──────────────────────────────────────────
CO_US_SISTEMA = "SA"
CO_SUCU       = "001"


def _log(nivel: str, mensaje: str, extra: dict = None) -> dict:
    """Registra una entrada en el rastro de ejecución."""
    entrada = {
        "ts":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "nivel":   nivel.upper(),   # INFO | OK | ERROR | WARN | SKIP
        "msg":     mensaje,
        **(extra or {}),
    }
    _rastro_memoria.append(entrada)
    if len(_rastro_memoria) > 500:
        _rastro_memoria.pop(0)
    # Persistir en archivo
    try:
        existing = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                existing = json.load(f)
        existing.append(entrada)
        existing = existing[-500:]   # máximo 500 entradas en archivo
        with open(LOG_FILE, "w") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    # También al logger estándar
    lvl = logging.ERROR if nivel == "ERROR" else logging.INFO
    logger.log(lvl, f"[BCV-TASA] {mensaje}")
    return entrada


def obtener_rastro(limite: int = 100) -> List[dict]:
    """Retorna las últimas N entradas del rastro (memoria + archivo)."""
    if _rastro_memoria:
        return _rastro_memoria[-limite:]
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                data = json.load(f)
            return data[-limite:]
    except Exception:
        pass
    return []


def limpiar_rastro():
    """Borra el rastro de ejecución."""
    global _rastro_memoria
    _rastro_memoria = []
    try:
        os.remove(LOG_FILE)
    except Exception:
        pass


# ── Scraper BCV ──────────────────────────────────────────────────────────────
BCV_URL     = "https://www.bcv.org.ve"
BCV_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Cache-Control": "no-cache",
}


def _parse_tasa_bcv(texto: str) -> Optional[float]:
    """Parsea un número venezolano con coma decimal: '563,29' → 563.29"""
    if not texto:
        return None
    clean = texto.strip().replace(".", "").replace(",", ".")
    m = re.search(r"\d+\.\d+", clean)
    if m:
        try:
            return round(float(m.group()), 2)
        except ValueError:
            return None
    return None


MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
}

def parse_spanish_date(text: str) -> Optional[date]:
    """Parsea una fecha en español (ej. 'Martes, 09 Junio 2026') a un objeto date."""
    if not text:
        return None
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    m = re.search(r'(\d+)\s+([a-zñáéíóú]+)\s+(\d{4})', text)
    if m:
        try:
            day = int(m.group(1))
            month_str = m.group(2)
            year = int(m.group(3))
            month_str = month_str.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            month = MESES_ES.get(month_str)
            if month:
                return date(year, month, day)
        except Exception as e:
            logger.error(f"Error parsing date parts: {e}")
    return None

def scrape_tasas_bcv() -> Tuple[Dict[str, Optional[float]], Optional[date]]:
    """
    Raspa bcv.org.ve y extrae las tasas de USD, EUR y la fecha valor de aplicación.
    Retorna: ({ 'USD': 563.29, 'EUR': 601.45 }, fecha_valor)
    """
    resultado = {k: None for k in MONEDAS_BCV}
    fecha_valor = None
    try:
        r = requests.get(BCV_URL, headers=BCV_HEADERS, timeout=15, verify=False)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # 1. Extraer tasas
        for cod, cfg in MONEDAS_BCV.items():
            div = soup.find("div", id=cfg["id_html"])
            if not div:
                section = soup.find("section", id=cfg["id_html"])
                div = section or div
            if div:
                strong = div.find("strong")
                texto  = strong.get_text(strip=True) if strong else div.get_text(strip=True)
                tasa   = _parse_tasa_bcv(texto)
                resultado[cod] = tasa

        # 2. Extraer fecha valor
        date_span = None
        for div in soup.find_all(["div", "span"]):
            if div.get_text() and "Fecha Valor:" in div.get_text():
                span = div.find("span", class_="date-display-single")
                if span:
                    date_span = span
                    break
        if not date_span:
            date_span = soup.find("span", class_="date-display-single")
        if date_span:
            fecha_valor = parse_spanish_date(date_span.get_text(strip=True))

        _log("INFO", f"BCV raspado OK → USD={resultado['USD']} EUR={resultado['EUR']} FechaValor={fecha_valor}")
    except requests.exceptions.SSLError:
        try:
            r = requests.get(BCV_URL, headers=BCV_HEADERS, timeout=15, verify=False)
            soup = BeautifulSoup(r.text, "html.parser")
            for cod, cfg in MONEDAS_BCV.items():
                div = soup.find("div", id=cfg["id_html"])
                if div:
                    strong = div.find("strong")
                    texto  = strong.get_text(strip=True) if strong else ""
                    resultado[cod] = _parse_tasa_bcv(texto)
            # Intentar también la fecha
            date_span = soup.find("span", class_="date-display-single")
            if date_span:
                fecha_valor = parse_spanish_date(date_span.get_text(strip=True))
        except Exception as e2:
            _log("ERROR", f"BCV SSL fallback error: {e2}")
    except Exception as e:
        _log("ERROR", f"Error raspando BCV: {e}", {"tb": traceback.format_exc()[-500:]})

    return resultado, fecha_valor


# ── Lógica de fecha de aplicación ────────────────────────────────────────────

def _siguiente_dia_habil(desde: date) -> date:
    """Retorna el siguiente día hábil (Lun-Vie) desde 'desde' inclusive."""
    d = desde + timedelta(days=1)
    while d.weekday() >= 5:   # 5=Sáb, 6=Dom
        d += timedelta(days=1)
    return d


def _fecha_aplicacion(fecha_publicacion: date = None) -> date:
    """
    La tasa publicada por BCV hoy (fecha_publicacion) aplica para el
    siguiente día hábil.
    """
    pub = fecha_publicacion or date.today()
    return _siguiente_dia_habil(pub)


# ── Operaciones en saTasa (Profit) ────────────────────────────────────────────

def _get_conn_profit():
    cfg = load_bcv_config()
    server = cfg["host"]
    if cfg.get("instance"):
        server = f"{server}\\{cfg['instance']}"
    if cfg.get("port"):
        server = f"{server},{cfg['port']}"
        
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={cfg['database']};"
        f"UID={cfg['user']};"
        f"PWD={cfg['password']};"
        "TrustServerCertificate=yes;Connection Timeout=10;"
    )
    return pyodbc.connect(conn_str, timeout=10)


def obtener_tasa_actual_profit(co_mone: str, fecha: date) -> Optional[float]:
    """Lee la tasa de saTasa para co_mone y fecha exacta."""
    try:
        conn = _get_conn_profit()
        cur  = conn.cursor()
        cur.execute(
            "SELECT tasa_c FROM saTasa WHERE co_mone=? AND CONVERT(date,fecha)=?",
            (co_mone, fecha.isoformat())
        )
        row = cur.fetchone()
        conn.close()
        return float(row[0]) if row else None
    except Exception as e:
        _log("ERROR", f"Error leyendo saTasa {co_mone}/{fecha}: {e}")
        return None


def obtener_tasa_activa_y_fecha_profit(co_mone: str, fecha: date) -> Tuple[Optional[float], Optional[date]]:
    """
    Busca la tasa de cambio activa en Profit para la fecha dada,
    es decir, la tasa registrada con la fecha más reciente que sea menor o igual a 'fecha'.
    Retorna: (tasa, fecha_valor)
    """
    try:
        conn = _get_conn_profit()
        cur  = conn.cursor()
        cur.execute(
            """SELECT TOP 1 tasa_c, fecha FROM saTasa
               WHERE co_mone=? AND CONVERT(date, fecha) <= ?
               ORDER BY fecha DESC""",
            (co_mone, fecha.isoformat())
        )
        row = cur.fetchone()
        conn.close()
        if row:
            tasa_val = float(row[0])
            fecha_val = row[1]
            if hasattr(fecha_val, "date"):
                fecha_val = fecha_val.date()
            elif isinstance(fecha_val, str):
                fecha_val = datetime.strptime(fecha_val.split(' ')[0], "%Y-%m-%d").date()
            return tasa_val, fecha_val
        return None, None
    except Exception as e:
        _log("ERROR", f"Error leyendo tasa activa y fecha Profit {co_mone}/{fecha}: {e}")
        return None, None



def upsert_tasa_profit(co_mone: str, fecha_aplicacion: date, tasa: float) -> bool:
    """
    Inserta o actualiza la tasa en saTasa para el día de aplicación.
    Aplica tanto a ventas (tasa_c) como a compras (tasa_v).
    """
    ahora = datetime.now()
    try:
        conn = _get_conn_profit()
        cur  = conn.cursor()

        # Verificar si ya existe el registro
        cur.execute(
            "SELECT COUNT(*) FROM saTasa WHERE co_mone=? AND CONVERT(date,fecha)=?",
            (co_mone, fecha_aplicacion.isoformat())
        )
        existe = cur.fetchone()[0] > 0

        if existe:
            cur.execute(
                """UPDATE saTasa
                   SET tasa_c=?, tasa_v=?,
                       co_us_mo=?, co_sucu_mo=?, fe_us_mo=?
                   WHERE co_mone=? AND CONVERT(date,fecha)=?""",
                (tasa, tasa,
                 CO_US_SISTEMA, CO_SUCU, ahora,
                 co_mone, fecha_aplicacion.isoformat())
            )
            accion = "UPDATE"
        else:
            cur.execute(
                """INSERT INTO saTasa
                   (co_mone, fecha, tasa_c, tasa_v,
                    co_us_in, co_sucu_in, fe_us_in,
                    co_us_mo, co_sucu_mo, fe_us_mo)
                   VALUES (?,?,?,?, ?,?,?, ?,?,?)""",
                (co_mone, fecha_aplicacion.isoformat(), tasa, tasa,
                 CO_US_SISTEMA, CO_SUCU, ahora,
                 CO_US_SISTEMA, CO_SUCU, ahora)
            )
            accion = "INSERT"

        conn.commit()
        conn.close()
        _log("OK", f"saTasa {accion} → {co_mone} fecha={fecha_aplicacion} tasa={tasa}",
             {"co_mone": co_mone, "fecha": fecha_aplicacion.isoformat(),
              "tasa": tasa, "accion": accion})
        return True

    except Exception as e:
        _log("ERROR", f"Error en upsert_tasa_profit {co_mone}/{fecha_aplicacion}: {e}",
             {"tb": traceback.format_exc()[-800:]})
        return False


# ── Ciclo principal de actualización ─────────────────────────────────────────

# Estado del ciclo actual (persiste en memoria entre llamadas del scheduler)
_estado_ciclo = {
    "fecha_busqueda":    None,   # date: fecha para la que está buscando
    "fecha_aplicacion":  None,   # date: fecha que insertará en saTasa
    "tasa_anterior_usd": None,   # float: tasa USD del día anterior (para detectar cambio)
    "tasa_anterior_eur": None,
    "completado":        False,  # True cuando ya actualizó exitosamente
    "intentos":          0,
    "ultima_ejecucion":  None,
}


def _leer_tasa_anterior(co_mone: str) -> Optional[float]:
    """Lee la tasa más reciente de saTasa (el día anterior al de aplicación)."""
    try:
        conn = _get_conn_profit()
        cur  = conn.cursor()
        cur.execute(
            """SELECT TOP 1 tasa_c FROM saTasa
               WHERE co_mone=?
               ORDER BY fecha DESC""",
            (co_mone,)
        )
        row = cur.fetchone()
        conn.close()
        return float(row[0]) if row else None
    except Exception:
        return None


def ejecutar_ciclo_bcv(forzar: bool = False) -> dict:
    """
    Lógica principal del ciclo BCV.
    Llamado por el scheduler cada 5 minutos entre 17:00 y 21:00, y manualmente.
    """
    global _estado_ciclo

    ahora      = datetime.now()
    hoy        = date.today()

    # Si ya completó para el día de hoy, no hacer nada (a menos que se fuerce)
    if (not forzar
            and _estado_ciclo["completado"]
            and _estado_ciclo["fecha_busqueda"] == hoy):
        _log("SKIP", f"Ciclo ya completado para hoy {hoy}. Próxima búsqueda mañana.")
        return {"estado": "ya_completado", "fecha": hoy.isoformat()}

    # Inicializar ciclo para un nuevo día
    if _estado_ciclo["fecha_busqueda"] != hoy:
        _estado_ciclo.update({
            "fecha_busqueda":    hoy,
            "fecha_aplicacion":  _fecha_aplicacion(hoy), # fallback inicial
            "tasa_anterior_usd": _leer_tasa_anterior("USD"),
            "tasa_anterior_eur": _leer_tasa_anterior("EUR"),
            "completado":        False,
            "intentos":          0,
        })
        _log("INFO", f"Nuevo ciclo iniciado. Buscando tasa BCV de hoy {hoy}.")

    # Pre-check: si no está forzado, verificar si ya existen ambas tasas en Profit para la fecha de aplicación teórica
    # para detener la búsqueda de inmediato sin raspar la web si ya están registradas.
    if not forzar:
        f_aplic_teorica = _fecha_aplicacion(hoy)
        usd_db = obtener_tasa_actual_profit("USD", f_aplic_teorica)
        eur_db = obtener_tasa_actual_profit("EUR", f_aplic_teorica)
        if usd_db is not None and eur_db is not None:
            _estado_ciclo["completado"] = True
            _estado_ciclo["fecha_aplicacion"] = f_aplic_teorica
            _log("SKIP", f"Tasas ya registradas en Profit para la fecha de aplicación {f_aplic_teorica} (USD={usd_db}, EUR={eur_db}). Se detiene la búsqueda hoy.")
            return {
                "skip_synced": True,
                "estado": "ya_registrado_db",
                "usd": usd_db,
                "eur": eur_db,
                "fecha_aplicacion": f_aplic_teorica.isoformat(),
                "intento": _estado_ciclo["intentos"]
            }

    _estado_ciclo["intentos"] += 1
    _estado_ciclo["ultima_ejecucion"] = ahora.isoformat()

    intento = _estado_ciclo["intentos"]
    _log("INFO", f"Intento #{intento} — {ahora.strftime('%H:%M:%S')} — raspando BCV...")

    # 1. Raspar BCV
    tasas_bcv, fecha_valor_bcv = scrape_tasas_bcv()
    usd_nuevo = tasas_bcv.get("USD")
    eur_nuevo = tasas_bcv.get("EUR")

    if not usd_nuevo and not eur_nuevo:
        _log("WARN", f"Intento #{intento}: BCV no devolvió tasas. Reintentando en 5 min.")
        return {"estado": "sin_datos", "intento": intento}

    # Definir fecha de aplicación exacta según el BCV
    if fecha_valor_bcv:
        f_aplic = fecha_valor_bcv
        _estado_ciclo["fecha_aplicacion"] = f_aplic
        _log("INFO", f"Fecha valor oficial extraída del BCV: {f_aplic}")
    else:
        f_aplic = _estado_ciclo["fecha_aplicacion"] or _fecha_aplicacion(hoy)
        _log("WARN", f"No se pudo extraer la fecha valor del BCV. Usando fecha calculada: {f_aplic}")

    # 2. Consultar si las tasas de USD y EUR ya están registradas en Profit para esta f_aplic
    usd_actual_db = obtener_tasa_actual_profit("USD", f_aplic)
    eur_actual_db = obtener_tasa_actual_profit("EUR", f_aplic)

    # Considerar "ya registrado" si los valores en DB coinciden con los del BCV
    usd_registrado = usd_actual_db is not None and abs(usd_actual_db - usd_nuevo) < 0.001
    eur_registrado = eur_actual_db is not None and abs(eur_actual_db - eur_nuevo) < 0.001

    if usd_registrado and eur_registrado and not forzar:
        _log("SKIP", f"Intento #{intento}: Tasas ya registradas en Profit para {f_aplic} (USD={usd_nuevo}, EUR={eur_nuevo}).")
        _estado_ciclo["completado"] = True # Evitar reintentar hoy
        return {
            "skip_synced": True,
            "estado": "ya_registrado", 
            "usd": usd_nuevo, 
            "eur": eur_nuevo, 
            "fecha_aplicacion": f_aplic.isoformat(), 
            "intento": intento
        }

    # 3. Actualizar saTasa en Profit para ambas monedas
    resultados = {}
    errores    = []

    for co_mone, tasa_nueva in [("USD", usd_nuevo), ("EUR", eur_nuevo)]:
        if not tasa_nueva:
            continue
        
        # Si no está forzado y esta moneda específica ya está registrada, la omitimos
        if not forzar:
            tasa_db = usd_actual_db if co_mone == "USD" else eur_actual_db
            if tasa_db is not None and abs(tasa_db - tasa_nueva) < 0.001:
                _log("INFO", f"{co_mone} ya registrada con la misma tasa {tasa_nueva} para {f_aplic}. Se omite.")
                resultados[co_mone] = {"tasa": tasa_nueva, "ok": True, "fecha_aplicacion": f_aplic.isoformat(), "accion": "SKIP"}
                continue

        ok = upsert_tasa_profit(co_mone, f_aplic, tasa_nueva)
        resultados[co_mone] = {"tasa": tasa_nueva, "ok": ok, "fecha_aplicacion": f_aplic.isoformat(), "accion": "UPSERT"}
        if not ok:
            errores.append(co_mone)

    if errores:
        _log("ERROR", f"Errores al guardar en Profit: {errores}")
        return {"estado": "error_profit", "errores": errores, "resultados": resultados}

    # 4. Marcar ciclo como completado
    _estado_ciclo["completado"] = True
    _log("OK",
         f"✅ CICLO COMPLETADO — Tasa BCV actualizada en Profit\n"
         f"   USD: {usd_nuevo} Bs/$ (aplicará el {f_aplic})\n"
         f"   EUR: {eur_nuevo} Bs/€ (aplicará el {f_aplic})\n"
         f"   Intentos: {intento}",
         {"usd": usd_nuevo, "eur": eur_nuevo, "fecha_aplicacion": f_aplic.isoformat()})

    return {
        "estado":          "completado",
        "fecha_aplicacion": f_aplic.isoformat(),
        "resultados":      resultados,
        "intentos":        intento,
    }


def estado_ciclo() -> dict:
    """Retorna el estado actual del ciclo de actualización."""
    return {
        **_estado_ciclo,
        "fecha_busqueda":   _estado_ciclo["fecha_busqueda"].isoformat()
            if _estado_ciclo["fecha_busqueda"] else None,
        "fecha_aplicacion": _estado_ciclo["fecha_aplicacion"].isoformat()
            if _estado_ciclo["fecha_aplicacion"] else None,
    }


def setup_bcv_scheduler(scheduler):
    """Registra la tarea programada para consultar y actualizar la tasa del BCV."""
    from apscheduler.triggers.cron import CronTrigger
    try:
        scheduler.add_job(
            ejecutar_ciclo_bcv,
            CronTrigger(day_of_week='mon-fri', hour='17-20', minute='*/5'),
            id='bcv_tasa_sync',
            replace_existing=True,
            kwargs={"forzar": False}
        )
        _log("INFO", "Programador de Tasa BCV registrado: Lun-Vie cada 5 min entre 17:00 y 21:00.")
        print("BCV Tasa Scheduler started: Mon-Fri every 5 min between 17:00 and 21:00.")
    except Exception as e:
        _log("ERROR", f"Error registrando el programador de Tasa BCV: {e}")
        print(f"Could not setup BCV scheduler: {e}")

