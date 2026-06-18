"""
Servicio Fuerza Móvil — API REST con Bearer Token
Documentación oficial:
  Base URL: suministrada por FM (actualmente http://fmdbelen.ddns.net:9595/FMDBELEN/public)
  Auth: Authorization: Bearer {token}
  Tipo: application/json (REST API)

Endpoints documentados:
  GET  api/auth/orders          → Pedidos aprobados
  POST api/auth/change_status   → Marcar pedidos como exportados
  GET  api/auth/receipts        → Recibos de cobro validados  ← PRINCIPAL PARA CXC
  POST api/auth/receipts_status → Marcar recibos como exportados
  GET  api/auth/coordenadas     → Coordenadas GPS

DICCIONARIO RECIBO (cabecera):
  num_recibo, cod_tipodoc, cod_cliente, cod_vendedor, fecha, hora,
  observ_regrecibo, numitem_fact, numitem_pagos, numitem_reten

DICCIONARIO PAGOS (formas de pago dentro del recibo):
  cod_regpago, id_app, num_recibo, monto_pago, fecha_pago,
  cod_regtipopago, cod_banco, num_referencia, observacion,
  fecha_registro, cod_moneda, cod_estatus_pago, tasa

DICCIONARIO FACTURAS (dentro del recibo):
  id_recfac, num_recibo, num_factura, fecha_vencimiento,
  monto_siniva, iva, total, cod_tipodoc, cod_vendedor,
  vendedor, cod_moneda
"""
import requests
import urllib3
import re
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import logging
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)

FM_BASE_URL    = os.getenv("FM_BASE_URL",   "http://fmdbelen.ddns.net:9595/FMDBELEN/public")
FM_BEARER_TOKEN = os.getenv("FM_TOKEN",     "")   # Token suministrado por FM
FM_TIMEOUT     = 20

# Endpoints documentados
FM_ENDPOINT_RECEIPTS        = "api/auth/receipts"
FM_ENDPOINT_RECEIPTS_STATUS = "api/auth/receipts_status"
FM_ENDPOINT_ORDERS          = "api/auth/orders"
FM_ENDPOINT_ORDERS_STATUS   = "api/auth/change_status"

# Configuración legacy (para compatibilidad con modal de Config FM)
FM_COBROS_ENDPOINT = FM_ENDPOINT_RECEIPTS
FM_COBROS_METHOD   = "GET"
FM_COBROS_P_DESDE  = ""      # GET api/auth/receipts no tiene parámetros de fecha
FM_COBROS_P_HASTA  = ""

# Credenciales web legacy (pantalla de login antigua, no usada en API REST)
FM_USUARIO  = "ocw"
FM_PASSWORD = "1111"

# Sesión global reutilizable
_fm_session: Optional[requests.Session] = None
_fm_logged_in: bool = False


# ─────────────────────────────────────────────
# Gestión de sesión FM
# ─────────────────────────────────────────────

def _get_csrf_token(s: requests.Session) -> Optional[str]:
    """Obtiene el CSRF token de la página de login de FM."""
    try:
        r = s.get(FM_BASE_URL + "/", timeout=FM_TIMEOUT, allow_redirects=True)
        if r.status_code != 200:
            logger.warning(f"FM login page status: {r.status_code}")
            return None
        # Campo: <input type="hidden" name="_token" id="token" value="...">
        m = re.search(r'name="_token"[^>]+value="([^"]+)"', r.text)
        if not m:
            m = re.search(r'id="token"[^>]+value="([^"]+)"', r.text)
        if not m:
            m = re.search(r'<meta name="csrf-token" content="([^"]+)"', r.text)
        return m.group(1) if m else None
    except Exception as e:
        logger.error(f"FM CSRF error: {e}")
        return None


def _fm_login(usuario: str = None, password: str = None) -> Optional[requests.Session]:
    """
    Crea una sesión autenticada con Fuerza Móvil.
    FM usa AJAX: devuelve "1" si login exitoso, "2" si credenciales incorrectas.
    """
    global _fm_session, _fm_logged_in

    usr = usuario or FM_USUARIO
    pwd = password or FM_PASSWORD

    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "es-VE,es;q=0.9",
    })

    csrf = _get_csrf_token(s)
    if not csrf:
        logger.error("FM: No se pudo obtener CSRF token")
        return None

    logger.info(f"FM: Intentando login AJAX con usuario={usr}")
    try:
        resp = s.post(
            FM_BASE_URL + "/login",
            data={"_token": csrf, "usuario": usr, "password": pwd},
            timeout=FM_TIMEOUT,
            allow_redirects=False,  # FM usa AJAX, no redirect
        )
        code = resp.text.strip()
        logger.info(f"FM: Login AJAX response code='{code}' status={resp.status_code}")

        # "1" = login exitoso, "2" = credenciales incorrectas
        if code == "1":
            logger.info(f"FM: Login exitoso para usuario={usr}")
            _fm_session  = s
            _fm_logged_in = True
            return s
        else:
            logger.warning(f"FM: Login falló para {usr}, código={code}")
            _fm_logged_in = False
            return None
    except Exception as e:
        logger.error(f"FM: Login exception: {e}")
        return None


def _get_session(force_new: bool = False) -> Optional[requests.Session]:
    """Retorna la sesión activa, haciendo login si es necesario."""
    global _fm_session, _fm_logged_in
    if not force_new and _fm_session and _fm_logged_in:
        return _fm_session
    return _fm_login()


def _fm_get(path: str, params: dict = None, s: requests.Session = None) -> Optional[Any]:
    """GET autenticado contra FM. Acepta JSON o HTML."""
    session = s or _get_session()
    if not session:
        return None
    url = FM_BASE_URL.rstrip("/") + path
    try:
        r = session.get(
            url,
            params=params or {},
            timeout=FM_TIMEOUT,
            allow_redirects=True,
            headers={"Accept": "application/json, text/html, */*",
                     "X-Requested-With": "XMLHttpRequest"},
        )
        # Si nos redirigió al login, la sesión expiró
        if "login" in r.url.lower():
            logger.warning("FM: sesión expirada, re-autenticando...")
            session = _fm_login()
            if not session:
                return None
            r = session.get(url, params=params or {}, timeout=FM_TIMEOUT, allow_redirects=True)

        if r.status_code != 200:
            logger.warning(f"FM GET {path}: {r.status_code}")
            return None

        # Intentar parsear como JSON primero
        try:
            return r.json()
        except Exception:
            return {"_html": r.text, "_url": r.url}
    except Exception as e:
        logger.error(f"FM GET {path}: {e}")
        return None


def _fm_post(path: str, data: dict = None, json_body: dict = None, s: requests.Session = None) -> Optional[Any]:
    """POST autenticado contra FM con renovación de CSRF."""
    session = s or _get_session()
    if not session:
        return None
    url = FM_BASE_URL.rstrip("/") + path
    try:
        csrf = _get_csrf_token(session)
        post_data = data or {}
        if csrf:
            post_data = {**post_data, "_token": csrf}

        r = session.post(
            url,
            data=post_data if not json_body else None,
            json=json_body,
            timeout=FM_TIMEOUT,
            allow_redirects=True,
            headers={"Accept": "application/json, text/html, */*",
                     "X-Requested-With": "XMLHttpRequest"},
        )
        try:
            return r.json()
        except Exception:
            return {"_html": r.text, "_status": r.status_code}
    except Exception as e:
        logger.error(f"FM POST {path}: {e}")
        return None


# ─────────────────────────────────────────────
# Parsear HTML de tabla FM
# ─────────────────────────────────────────────

def _parse_html_table(html: str) -> List[Dict]:
    """
    Extrae filas de la primera tabla HTML de la respuesta FM.
    Retorna lista de dicts con keys = headers de la tabla.
    """
    if not html:
        return []

    # Extraer headers <th>
    headers = re.findall(r'<th[^>]*>(.*?)</th>', html, re.IGNORECASE | re.DOTALL)
    headers = [re.sub(r'<[^>]+>', '', h).strip() for h in headers]

    # Extraer filas <tr>
    rows_raw = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.IGNORECASE | re.DOTALL)
    result = []
    for row_html in rows_raw:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.IGNORECASE | re.DOTALL)
        if not cells:
            continue
        cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
        if len(cells) >= 2:
            row_dict = {}
            for i, h in enumerate(headers):
                if i < len(cells):
                    row_dict[h] = cells[i]
                else:
                    row_dict[h] = ""
            # Si no hay headers suficientes usar índices
            if not headers:
                row_dict = {str(i): v for i, v in enumerate(cells)}
            result.append(row_dict)
    return result


# ─────────────────────────────────────────────
# Endpoints públicos
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# API REST con Bearer Token (según documentación oficial)
# ─────────────────────────────────────────────

def _bearer_headers() -> Dict:
    """Headers con Bearer Token para la API REST de FM."""
    headers = {
        "Accept":        "application/json",
        "Content-Type":  "application/json",
    }
    if FM_BEARER_TOKEN:
        headers["Authorization"] = f"Bearer {FM_BEARER_TOKEN}"
    return headers


def get_receipts(token: str = "") -> List[Dict]:
    """
    GET api/auth/receipts — Recibos de cobro validados (estatus Aprobado).
    Sin parámetros de fecha — retorna los pendientes de exportar.

    Respuesta normalizada al formato interno del visor CXC:
      fm_id, cod_cliente, fecha, monto, tipo_pago, referencia,
      cod_banco, cod_moneda, tasa, facturas_afectadas
    """
    tok = token or FM_BEARER_TOKEN
    url = FM_BASE_URL.rstrip("/") + "/" + FM_ENDPOINT_RECEIPTS.lstrip("/")
    headers = {
        "Accept":        "application/json",
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {tok}" if tok else "",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=FM_TIMEOUT, verify=False)
        if resp.status_code == 401:
            logger.error("FM api/auth/receipts: 401 Unauthorized — token inválido o no configurado")
            return []
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"get_receipts error: {e}")
        return []

    # Normalizar — cada item de data[] es un dict {Recibo, Pagos, Facturas, ...}
    recibos = data if isinstance(data, list) else data.get("data", data.get("receipts", []))
    resultado = [_normalize_receipt(r) for r in recibos if isinstance(r, dict)]
    return [r for r in resultado if r is not None]  # excluir recibos sin pagos


def _clasificar_tipo_pago(cod: str) -> Dict:
    """
    Clasifica el tipo de pago segun cod_regtipopago del documento FM.

    Catálogo REAL verificado contra datos vivos del API FM (junio 2026):
      '01' = Transferencia      (65 pagos confirmados)
      '05' = Pago Móvil Bs.    (P2P, 4 pagos confirmados  — Profit lo muestra como 'Pago Movil Bs.')

    Códigos adicionales (no vistos aún pero incluidos por consistencia con
    la numeración estándar del sistema FM):
      '02' = Efectivo
      '03' = Pago Móvil C2P   (Cobro a Persona, iniciado por comercio)
      '04' = Cheque
      '06' = Tarjeta Crédito
      '07' = Tarjeta Débito
    """
    # Normalizar: quitar ceros a la izquierda
    cod_norm = str(cod).strip().lstrip('0') or '0'
    catalogo = {
        '1': {"tipo": "transferencia", "label": "Transferencia",   "icono": "🏦",
              "requiere_banco": True,  "metodo_banco": "transferencia"},
        '2': {"tipo": "efectivo",      "label": "Efectivo",         "icono": "💵",
              "requiere_banco": False, "metodo_banco": None},
        '3': {"tipo": "c2p",           "label": "Pago Móvil C2P",   "icono": "📱",
              "requiere_banco": True,  "metodo_banco": "pago_movil"},
        '4': {"tipo": "transferencia", "label": "Cheque",           "icono": "✍️",
              "requiere_banco": True,  "metodo_banco": "transferencia"},
        '5': {"tipo": "pago_movil",    "label": "Pago Móvil Bs.",   "icono": "📱",
              "requiere_banco": True,  "metodo_banco": "pago_movil"},
        '6': {"tipo": "tarjeta",       "label": "Tarjeta Créd.",    "icono": "💳",
              "requiere_banco": True,  "metodo_banco": "tarjeta"},
        '7': {"tipo": "tarjeta",       "label": "Tarjeta Déb.",     "icono": "💳",
              "requiere_banco": True,  "metodo_banco": "tarjeta"},
    }
    return catalogo.get(cod_norm, {
        "tipo": "transferencia", "label": "Transferencia", "icono": "🏦",
        "requiere_banco": True,  "metodo_banco": "transferencia"
    })


def _normalizar_cod_banco(cod: str) -> str:
    """'0102-1' → '0102',  '040161' → '0401'  (toma los primeros 4 dígitos)."""
    limpio = str(cod or "").split("-")[0].strip()
    return limpio[:4].zfill(4) if limpio else ""


def _normalize_receipt(r: Dict) -> Dict:
    """
    Convierte un recibo del API FM al formato completo del visor CXC.

    Estructura REAL verificada de api/auth/receipts:
      {
        "Recibo":  [ { num_recibo, cod_cliente, cod_vendedor, fecha, hora, ... } ],
        "Pagos":   [ { num_recibo, cod_regpago, monto_pago, fecha_pago,
                       cod_regtipopago, cod_banco, num_referencia,
                       cod_moneda, tasa, cod_estatus_pago } ],
        "Facturas":[], "Retenciones":[], "Imagenes":[]
      }

    REGLA: toda la informacion del pago se lee desde Pagos[].
    De Recibo[0] solo tomamos: cod_cliente, cod_vendedor, hora, observ_regrecibo.
    num_recibo viene de Pagos[0].num_recibo (es la fuente de verdad del pago).
    """
    # ── Cabecera del recibo (solo datos de identidad del cliente) ──
    recibo_arr = r.get("Recibo", [])
    cab        = recibo_arr[0] if recibo_arr else {}

    cod_cliente  = str(cab.get("cod_cliente",  "")).strip()
    cod_vendedor = str(cab.get("cod_vendedor", "")).strip()
    hora         = str(cab.get("hora",         "")).strip()
    observacion  = str(cab.get("observ_regrecibo", "")).strip()

    # ── Pagos: fuente principal de todos los campos financieros ──
    pagos    = r.get("Pagos",    r.get("pagos",    []))
    facturas = r.get("Facturas", r.get("facturas", []))
    # ── Imágenes adjuntas al recibo (URL directa al servidor FM) ──
    imagenes_fm = r.get("Imagenes", r.get("imagenes", []))
    # Normalizar: extraer solo ruta_img válidas
    imagenes_urls = [
        img.get("ruta_img", "") for img in imagenes_fm
        if isinstance(img, dict) and img.get("ruta_img")
    ]

    if not pagos:
        return None  # recibo sin pagos, ignorar

    # ── Procesar cada pago ──
    pagos_procesados = []
    monto_ves_total  = 0.0
    tipo_principal   = {}
    ref_principal    = ""
    num_recibo       = ""
    fecha_pago       = str(cab.get("fecha", ""))

    for i, p in enumerate(pagos):
        # Leer TODOS los campos desde Pagos
        num_recibo_p  = str(p.get("num_recibo",       "")).strip()
        monto_p       = float(p.get("monto_pago",     0) or 0)
        fecha_p       = str(p.get("fecha_pago",       fecha_pago)).strip()
        cod_tipo      = str(p.get("cod_regtipopago",  "01")).strip()
        cod_banco_p   = str(p.get("cod_banco",        "")).strip()
        num_ref_p     = str(p.get("num_referencia",   "")).strip()
        observ_p      = str(p.get("observacion",      "")).strip()
        cod_moneda_p  = str(p.get("cod_moneda",       "BS")).upper()
        tasa_p        = float(p.get("tasa",           0) or 0)
        estatus_pago  = p.get("cod_estatus_pago",      0)

        # Clasificar tipo de pago
        clasificacion = _clasificar_tipo_pago(cod_tipo)

        # Calcular USD (FM usa BS = bolivares)
        es_bs = cod_moneda_p in ("BS", "VES", "BS.")
        if not es_bs:
            monto_usd_p = monto_p
        elif tasa_p > 0:
            monto_usd_p = round(monto_p / tasa_p, 2)
        else:
            monto_usd_p = 0.0

        monto_ves_total += monto_p

        # Normalizar código de banco (FM envía formatos no estándar)
        cod_banco_norm = _normalizar_cod_banco(cod_banco_p)

        pago_proc = {
            # Campos raw de Pagos
            "num_recibo":        num_recibo_p,
            "cod_regpago":       p.get("cod_regpago", 0),
            "monto_pago":        monto_p,
            "fecha_pago":        fecha_p,
            "cod_regtipopago":   cod_tipo,
            "cod_banco":         cod_banco_norm,   # normalizado 4 dígitos
            "cod_banco_raw":      cod_banco_p,      # valor original FM (auditoría)
            "num_referencia":    num_ref_p,
            "observacion":       observ_p,
            "cod_moneda":        cod_moneda_p,
            "tasa":              tasa_p,
            "cod_estatus_pago":  estatus_pago,
            # Campos calculados
            "_tipo":             clasificacion["tipo"],
            "_label":            clasificacion["label"],
            "_icono":            clasificacion["icono"],
            "_requiere_banco":   clasificacion["requiere_banco"],
            "_metodo_banco":     clasificacion["metodo_banco"],
            "_monto_usd":        monto_usd_p,
        }
        pagos_procesados.append(pago_proc)

        # El primer pago define los campos principales del recibo
        if i == 0:
            num_recibo     = num_recibo_p
            fecha_pago     = fecha_p
            tipo_principal = clasificacion
            ref_principal  = num_ref_p

    # ── Totales del recibo ──
    monto_ves = round(monto_ves_total, 2)
    pago_ref  = pagos[0]
    tasa      = float(pago_ref.get("tasa", 0) or 0)
    moneda    = str(pago_ref.get("cod_moneda", "BS")).upper()
    es_bs     = moneda in ("BS", "VES", "BS.")
    monto_usd = round(monto_ves / tasa, 2) if (es_bs and tasa > 0) else monto_ves

    monto_facturas_fm = sum(
        float(f.get("total", f.get("pago", 0)) or 0) for f in facturas
    )

    return {
        # Identificacion — num_recibo desde Pagos (fuente de verdad)
        "fm_id":           num_recibo,
        "num_recibo":      num_recibo,
        "cod_cliente":     cod_cliente,
        "cliente_id":      cod_cliente,
        "cliente_nombre":  "",          # se enriquece desde Profit en el endpoint
        "cod_vendedor":    cod_vendedor,
        "fecha":           fecha_pago,
        "hora":            hora,
        "observacion":     observacion,

        # Montos (de Pagos)
        "monto":           monto_ves,
        "monto_usd":       monto_usd,
        "tasa":            tasa,
        "cod_moneda":      moneda,

        # Tipo de pago clasificado (de Pagos[0].cod_regtipopago)
        "tipo_pago":       tipo_principal.get("tipo",           "transferencia"),
        "tipo_label":      tipo_principal.get("label",          "Transferencia"),
        "tipo_icono":      tipo_principal.get("icono",          "🏦"),
        "requiere_banco":  tipo_principal.get("requiere_banco", True),
        "metodo_banco":    tipo_principal.get("metodo_banco",   "transferencia"),
        # Código raw de FM para auditoría / detección de discrepancias con Profit
        "cod_regtipopago_fm": str(pagos[0].get("cod_regtipopago", "") if pagos else ""),

        # Referencia bancaria (de Pagos[0].num_referencia y cod_banco)
        "referencia":      ref_principal,
        "cod_banco":       _normalizar_cod_banco(str(pago_ref.get("cod_banco", "")).strip()),
        "cod_banco_raw":   str(pago_ref.get("cod_banco", "")).strip(),
        "telefono":        "",          # se enriquece desde Profit

        # ── Imágenes adjuntas (URLs al servidor FM) ──────────────
        "imagenes_urls":  imagenes_urls,     # lista de URLs de imagen
        "tiene_imagen":   len(imagenes_urls) > 0,

        # Detalle completo de pagos
        "pagos":               pagos_procesados,
        "num_pagos":           len(pagos_procesados),   # 1=normal, >1=multi-pago
        "facturas_fm":         facturas,
        "monto_facturas_fm":   monto_facturas_fm,

        # Estado
        "exportado":   False,
        "_fuente":     "fm_api",
        "_estatus":    "pendiente",
        "_tarea":      "adelanto",
    }



def mark_receipts_exported(num_recibos: List[str], token: str = "") -> bool:
    """
    POST api/auth/receipts_status
    Marca los recibos como exportados para que no vuelvan a aparecer.
    Retorna True si exitoso.
    """
    tok = token or FM_BEARER_TOKEN
    url = FM_BASE_URL.rstrip("/") + "/" + FM_ENDPOINT_RECEIPTS_STATUS.lstrip("/")
    try:
        resp = requests.post(
            url,
            json={"num_recibo": num_recibos},
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {tok}" if tok else "",
            },
            timeout=FM_TIMEOUT,
            verify=False,
        )
        result = resp.json()
        return bool(result) if isinstance(result, bool) else result.get("success", False)
    except Exception as e:
        logger.error(f"mark_receipts_exported error: {e}")
        return False


def get_fm_status() -> Dict:
    """
    Verifica la conectividad HTTP con Fuerza Móvil (sin login completo).
    El login se hace solo cuando se solicitan datos reales.
    """
    try:
        r = requests.get(FM_BASE_URL + "/", timeout=8, allow_redirects=True)
        if r.status_code == 200:
            # FM responde — verificar si la sesión actual está activa
            logged = _fm_logged_in and _fm_session is not None
            return {
                "status": "online" if logged else "reachable",
                "logged": logged,
                "url": FM_BASE_URL,
                "usuario": FM_USUARIO if logged else None,
            }
        return {"status": "offline", "reason": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"status": "offline", "reason": str(e)}


def fm_login_config(usuario: str, password: str) -> Dict:
    """Actualiza credenciales FM en runtime y prueba el login."""
    global FM_USUARIO, FM_PASSWORD
    FM_USUARIO = usuario
    FM_PASSWORD = password
    s = _fm_login(usuario, password)
    return {"status": "ok" if s else "error", "logged": bool(s)}


def get_cobros(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    cliente_id: Optional[str] = None,
    vendedor_id: Optional[str] = None,
) -> List[Dict]:
    """
    Obtiene cobros de Fuerza Móvil usando el endpoint configurado.
    """
    if not fecha_desde:
        fecha_desde = (date.today() - timedelta(days=30)).isoformat()
    if not fecha_hasta:
        fecha_hasta = date.today().isoformat()

    # Usar configuración dinámica
    endpoint = FM_COBROS_ENDPOINT
    method   = FM_COBROS_METHOD
    p_desde  = FM_COBROS_P_DESDE
    p_hasta  = FM_COBROS_P_HASTA

    params = {p_desde: fecha_desde, p_hasta: fecha_hasta}
    if cliente_id:
        params["cliente_id"] = cliente_id
    if vendedor_id:
        params["vendedor_id"] = vendedor_id

    # Obtener CSRF y hacer la petición
    import requests as _r
    s = _r.Session()
    s.headers.update({"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})

    try:
        r0 = s.get(FM_BASE_URL + "/", timeout=FM_TIMEOUT)
        m = re.search(r'name="_token" id="token" value="([^"]+)"', r0.text)
        csrf = m.group(1) if m else ""

        url = FM_BASE_URL.rstrip("/") + "/" + endpoint.lstrip("/")

        if method == "POST":
            resp = s.post(url, data={**params, "_token": csrf}, timeout=FM_TIMEOUT)
        else:
            resp = s.get(url, params=params, timeout=FM_TIMEOUT)

        if resp.status_code not in [200, 201]:
            logger.warning(f"FM GET cobros HTTP {resp.status_code}")
            return []

        try:
            data = resp.json()
        except Exception:
            # Intentar parsear tabla HTML
            rows = _parse_html_table(resp.text)
            if rows:
                return [_map_cobro_html(r, endpoint) for r in rows]
            return []

        cobros = _normalize_cobros(data, endpoint)
        logger.info(f"FM: {len(cobros)} cobros desde {endpoint}")
        return cobros

    except Exception as e:
        logger.error(f"FM get_cobros error: {e}")
        return []


def _normalize_cobros(data: Any, source_path: str) -> List[Dict]:
    """Normaliza respuesta JSON de FM."""
    if data is None:
        return []
    if isinstance(data, dict):
        for key in ["data", "cobros", "recibos", "pagos", "results", "items", "registros"]:
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
        if isinstance(data, dict):
            return [_map_cobro(data, source_path)]
    if not isinstance(data, list):
        return []
    return [_map_cobro(item, source_path) for item in data if isinstance(item, dict)]


def _map_cobro(item: Dict, source_path: str) -> Dict:
    """Mapea un registro JSON de FM al formato estándar."""
    def g(d, *keys):
        for k in keys:
            if k in d:
                return d[k]
        return None

    return {
        "fm_id": str(g(item, "id", "ID", "codigo", "Codigo", "recibo", "numero", "nro") or ""),
        "fecha": str(g(item, "fecha", "Fecha", "date", "fecha_cobro", "created_at") or ""),
        "cliente_id": str(g(item, "cliente_id", "ClienteId", "id_cliente", "cod_cliente", "CodigoCliente") or ""),
        "cliente_nombre": str(g(item, "cliente", "Cliente", "nombre_cliente", "NombreCliente", "razon_social", "nombre") or ""),
        "monto": float(g(item, "monto", "Monto", "amount", "importe", "total", "Total", "valor") or 0),
        "referencia": str(g(item, "referencia", "Referencia", "ref", "numero_ref", "nro_referencia", "nro") or ""),
        "vendedor_id": str(g(item, "vendedor_id", "VendedorId", "id_vendedor") or ""),
        "vendedor_nombre": str(g(item, "vendedor", "Vendedor", "nombre_vendedor", "NombreVendedor", "vendedor_name") or ""),
        "tipo_pago": _normalizar_tipo_pago(str(g(item, "tipo_pago", "TipoPago", "forma_pago", "metodo_pago", "tipo", "modalidad") or "")),
        "banco": str(g(item, "banco", "Banco", "banco_origen") or ""),
        "telefono": str(g(item, "telefono", "Telefono", "phone", "celular", "movil", "tlf") or ""),
        "cedula": str(g(item, "cedula", "Cedula", "rif", "dni", "documento", "doc") or ""),
        "moneda": str(g(item, "moneda", "Moneda", "currency", "divisa") or "VES"),
        "_source": source_path,
    }


def _map_cobro_html(row: Dict, source_path: str) -> Dict:
    """Mapea una fila de tabla HTML de FM al formato estándar."""
    # Intento de mapeo por nombres de columna comunes en español
    def g(d, *keys):
        for k in keys:
            for dk in d:
                if k.lower() in dk.lower():
                    return d[dk]
        return ""

    monto_raw = g(row, "monto", "total", "importe", "valor", "amount")
    try:
        monto = float(str(monto_raw).replace(",", ".").replace(".", "", str(monto_raw).count(".") - 1) if monto_raw else 0)
    except Exception:
        monto = 0.0

    return {
        "fm_id": str(g(row, "id", "nro", "numero", "recibo", "codigo") or list(row.values())[0] if row else ""),
        "fecha": str(g(row, "fecha", "date", "dia")),
        "cliente_id": str(g(row, "cod_cli", "cliente_id", "codigo_cliente", "cod_client")),
        "cliente_nombre": str(g(row, "cliente", "nombre", "razon", "name")),
        "monto": monto,
        "referencia": str(g(row, "referencia", "ref", "comprobante", "nro_ref")),
        "vendedor_id": str(g(row, "vendedor_id", "cod_vend")),
        "vendedor_nombre": str(g(row, "vendedor", "nombre_vendedor")),
        "tipo_pago": _normalizar_tipo_pago(str(g(row, "tipo", "forma_pago", "modalidad", "metodo"))),
        "banco": str(g(row, "banco", "bank")),
        "telefono": str(g(row, "telefono", "tlf", "movil", "celular")),
        "cedula": str(g(row, "cedula", "rif", "dni", "documento")),
        "moneda": "VES",
        "_source": source_path + "_html",
        "_raw_html": row,
    }


def _normalizar_tipo_pago(tipo: str) -> str:
    """Normaliza el tipo de pago a las categorías estándar."""
    t = tipo.lower()
    if any(k in t for k in ["c2p", "movil", "móvil", "pago movil", "pm"]):
        return "c2p"
    if any(k in t for k in ["transfer", "transf"]):
        return "transferencia"
    if any(k in t for k in ["tarjeta", "tdd", "tdc", "debito", "crédito", "credito"]):
        return "tarjeta"
    if any(k in t for k in ["efectivo", "cash"]):
        return "efectivo"
    return tipo or "otro"


def discover_endpoints() -> Dict[str, Any]:
    """Descubre endpoints disponibles en FM."""
    s = _get_session()
    results = {}
    if not s:
        return {"error": "no_session"}
    for name in ["cobros", "recibos", "pagos", "clientes", "movimientos", "home", "dashboard"]:
        data = _fm_get("/" + name, s=s)
        results[name] = {
            "available": data is not None,
            "is_json": isinstance(data, dict) and "_html" not in data or isinstance(data, list),
        }
    return results
