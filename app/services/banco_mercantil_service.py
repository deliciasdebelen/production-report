"""
Servicio para consumir la API de Mercantil Banco (sandbox).
Busca movimientos bancarios (C2P, TDD, Transferencias) para conciliación CXC.
Ref: https://apimbu.mercantilbanco.com/mercantil-banco/sandbox/v1/
"""
import requests
import logging
import os
from typing import Optional, Dict, Any, List
from datetime import date, timedelta

logger = logging.getLogger(__name__)

MERCANTIL_BASE_URL = os.getenv(
    "MERCANTIL_API_URL",
    "https://apimbu.mercantilbanco.com/mercantil-banco/sandbox/v1"
)
MERCANTIL_CLIENT_ID = os.getenv("MERCANTIL_CLIENT_ID", "cambiame")

# Identificadores del comercio (sandbox)
MERCHANT_ID = {
    "integratorId": 31,
    "merchantId": 123456,
    "terminalId": "abcde",
}

CLIENT_IDENTIFY = {
    "ipaddress": "127.0.0.1",
    "browser_agent": "CarmalCXC/1.0",
    "mobile": {"manufacturer": "Server"},
}


def _post(path: str, payload: Dict) -> Optional[Dict]:
    """POST genérico a la API de Mercantil."""
    url = MERCANTIL_BASE_URL.rstrip("/") + path
    headers = {
        "X-IBM-Client-ID": MERCANTIL_CLIENT_ID,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        logger.error(f"Mercantil HTTP error ({path}): {e} — {resp.text[:300]}")
        try:
            return resp.json()
        except Exception:
            return {"error": str(e), "status_code": resp.status_code}
    except Exception as e:
        logger.error(f"Mercantil error ({path}): {e}")
        return {"error": str(e)}


def buscar_pago_c2p(
    monto: float,
    telefono_destino: str,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> Dict:
    """
    Busca un pago C2P (Pago Móvil) en el banco.
    POST /mobile-payment/search
    """
    if not fecha_desde:
        fecha_desde = (date.today() - timedelta(days=7)).isoformat()
    if not fecha_hasta:
        fecha_hasta = date.today().isoformat()

    payload = {
        "merchant_identify": MERCHANT_ID,
        "client_identify": CLIENT_IDENTIFY,
        "search_by": {
            "amount": monto,
            "currency": "ves",
            "destinantion_mobile_number": telefono_destino,
            "date_from": fecha_desde,
            "date_to": fecha_hasta,
        },
    }
    result = _post("/mobile-payment/search", payload)
    return _normalize_banco_response(result, "c2p")


def buscar_pago_tarjeta(
    monto: float,
    numero_tarjeta_enc: str = "",
    referencia: str = "",
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> Dict:
    """
    Busca un pago con tarjeta (TDD/TDC).
    POST /payment/search
    """
    if not fecha_desde:
        fecha_desde = (date.today() - timedelta(days=7)).isoformat()
    if not fecha_hasta:
        fecha_hasta = date.today().isoformat()

    payload = {
        "merchant_identify": MERCHANT_ID,
        "client_identify": CLIENT_IDENTIFY,
        "search_by": {
            "trx_type": "compra",
            "amount": monto,
            "currency": "ves",
            "date_from": fecha_desde,
            "date_to": fecha_hasta,
        },
    }
    if referencia:
        payload["search_by"]["reference"] = referencia

    result = _post("/payment/search", payload)
    return _normalize_banco_response(result, "tarjeta")


def buscar_transferencia(
    monto: float,
    cedula_origen: str = "",
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> Dict:
    """
    Busca una transferencia bancaria.
    POST /payment/transfer-search
    """
    if not fecha_desde:
        fecha_desde = (date.today() - timedelta(days=7)).isoformat()
    if not fecha_hasta:
        fecha_hasta = date.today().isoformat()

    payload = {
        "merchant_identify": MERCHANT_ID,
        "client_identify": CLIENT_IDENTIFY,
        "search_by": {
            "amount": monto,
            "currency": "ves",
            "date_from": fecha_desde,
            "date_to": fecha_hasta,
        },
    }
    if cedula_origen:
        payload["search_by"]["origin_id"] = cedula_origen

    result = _post("/payment/transfer-search", payload)
    return _normalize_banco_response(result, "transferencia")


# ── Parrilla de bancos venezolanos (para resolución de nombres) ──
BANCOS_VE_MAP = {
    "0001": "BCV",                       "0102": "Banco de Venezuela",
    "0104": "Venezolano de Crédito",     "0105": "Mercantil",
    "0108": "BBVA Provincial",           "0114": "Bancaribe",
    "0115": "Banco Exterior",            "0128": "Banco Caroní",
    "0134": "Banesco",                   "0137": "Sofitasa",
    "0138": "Banco Plaza",               "0146": "Bangente",
    "0151": "BFC",                       "0156": "100% Banco",
    "0157": "Del Sur",                   "0163": "Banco del Tesoro",
    "0166": "Agrícola de Venezuela",     "0168": "Bancrecer",
    "0169": "Mi Banco",                  "0171": "Banco Activo",
    "0172": "Bancamiga",                 "0173": "BID",
    "0174": "Banplus",                   "0175": "Banco Digital Trabajadores",
    "0177": "BANFANB",                   "0178": "N58 Banco Digital",
    "0191": "BNC",                       "0601": "IMCP",
}


def _normalizar_cod_banco(cod: str) -> str:
    """'0102-1' → '0102',  '040161' → '0401'  (toma los primeros 4 dígitos)."""
    limpio = str(cod or "").split("-")[0].strip()
    return limpio[:4].zfill(4) if limpio else ""


# ── Caché de configuraciones de banco (leídas desde BD) ──────────────
import time as _time
_banco_cfg_cache: Dict = {}
_banco_cfg_ts: float   = 0
_BANCO_CFG_TTL: float  = 60.0   # renovar cada 60 s


def _get_bancos_config() -> Dict[str, Dict]:
    """Lee bancos_configuracion de la BD y lo cachea por TTL segundos."""
    global _banco_cfg_cache, _banco_cfg_ts
    now = _time.time()
    if _banco_cfg_cache and (now - _banco_cfg_ts) < _BANCO_CFG_TTL:
        return _banco_cfg_cache
    try:
        import sqlite3, os
        db_url = os.getenv("DATABASE_URL", "")
        is_pg  = "postgresql" in db_url or "postgres" in db_url
        if is_pg:
            import psycopg2
            from urllib.parse import urlparse
            u    = urlparse(db_url)
            conn = psycopg2.connect(
                host=u.hostname, port=u.port or 5432,
                dbname=u.path.lstrip("/"), user=u.username, password=u.password
            )
        else:
            conn = sqlite3.connect("/app/production.db")
            conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM bancos_configuracion WHERE activo = 1")
        rows = {str(r["codigo_banco"]).zfill(4): dict(r) for r in cur.fetchall()}
        conn.close()
        _banco_cfg_cache = rows
        _banco_cfg_ts    = now
        return rows
    except Exception as e:
        logger.warning(f"No se pudo leer bancos_configuracion: {e}")
        return {}


def _limpiar_cache_bancos():
    """Fuerza renovación del caché en la próxima llamada."""
    global _banco_cfg_ts
    _banco_cfg_ts = 0


def validar_pago_fm(pago_fm: Dict) -> Dict:
    """
    Enrutador bancario inteligente — configurable desde BD.

    Flujo:
      1. Lee cod_banco del pago FM (Pagos[0].cod_banco).
      2. Busca configuración activa en `bancos_configuracion`.
      3. Si hay config → llama al adaptador según tipo_api:
           bnc       → banco_bnc_service (credenciales de BD o env)
           mercantil → banco_mercantil_service
           (otros)   → marcado como pendiente de integración
      4. Si no hay config → devuelve banco detectado + "no configurado".
    """
    tipo   = pago_fm.get("metodo_banco") or pago_fm.get("tipo_pago", "transferencia")
    monto  = float(pago_fm.get("monto", 0))
    ref    = str(pago_fm.get("referencia", "")).strip()
    tel    = str(pago_fm.get("telefono",   "")).strip()
    fecha  = str(pago_fm.get("fecha",      "")).strip()

    # ── Detectar banco desde Pagos.cod_banco ──
    pagos     = pago_fm.get("pagos", [])
    cod_raw   = (pagos[0].get("cod_banco", "") if pagos else "") or pago_fm.get("cod_banco", "")
    cod_banco = _normalizar_cod_banco(cod_raw)
    banco_nom = BANCOS_VE_MAP.get(cod_banco, f"Banco {cod_banco}" if cod_banco else "Desconocido")

    # ── Efectivo: sin validación bancaria ──
    if tipo == "efectivo":
        return {
            "confirmado": True, "tipo": "efectivo", "tipo_label": "Efectivo",
            "banco": "—", "banco_nombre": "—", "codigo_banco": "—",
            "referencia_banco": "EFECTIVO", "monto_confirmado": monto,
            "fecha_banco": fecha, "mensaje": "Pago en efectivo — sin validación bancaria",
            "raw": None,
        }

    # ── Base de respuesta con banco detectado ──
    base = {
        "banco":        banco_nom,
        "banco_nombre": banco_nom,
        "codigo_banco": cod_banco or cod_raw,
        "tipo":         tipo,
        "referencia":   ref,
    }

    # ── Leer configuración desde BD ──
    cfgs = _get_bancos_config()
    cfg  = cfgs.get(cod_banco)

    if not cfg:
        return {**base, "confirmado": False, "monto_confirmado": 0,
                "integrado": False,
                "mensaje": f"{banco_nom} — sin configuración en BD. "
                           f"Agrégalo en ⚙️ Config → Bancos. Ref: {ref}"}

    tipo_api = cfg.get("tipo_api", "rest")

    # ── Adaptador BNC ──
    if tipo_api == "bnc":
        from app.services.banco_bnc_service import (
            buscar_transferencia_bnc, buscar_c2p_bnc, bnc_disponible,
        )
        import os
        # Sobreescribir env vars si hay credenciales en BD
        cg = cfg.get("client_guid") or ""
        mk = cfg.get("master_key")  or ""
        if cg: os.environ["BNC_CLIENT_GUID"] = cg
        if mk: os.environ["BNC_MASTER_KEY"]  = mk

        if not bnc_disponible():
            return {**base, "confirmado": False, "monto_confirmado": 0,
                    "mensaje": "BNC detectado pero credenciales no configuradas. "
                               "Ingresa ClientGUID y MasterKey en ⚙️ Config → Bancos"}
        if tipo == "c2p":
            result = buscar_c2p_bnc(ref, monto, tel, fecha)
        else:
            result = buscar_transferencia_bnc(ref, monto, fecha)
        return {**base, **result}

    # ── Adaptador Mercantil ──
    if tipo_api == "mercantil":
        return {**base, "confirmado": False, "monto_confirmado": 0,
                "integrado": True,
                "mensaje": f"Mercantil en proceso de integración. Ref: {ref}"}

    # ── REST genérico (placeholder para futuros bancos) ──
    if tipo_api in ("rest", "bnv", "banesco", "soap", "custom"):
        base_url = cfg.get("base_url", "")
        return {**base, "confirmado": False, "monto_confirmado": 0,
                "integrado": True,
                "mensaje": f"{banco_nom} ({tipo_api.upper()}) — conector en desarrollo. "
                           f"URL: {base_url or 'no configurada'}. Ref: {ref}"}

    return {**base, "confirmado": False, "monto_confirmado": 0,
            "integrado": False,
            "mensaje": f"{banco_nom} — tipo API '{tipo_api}' no reconocido. Ref: {ref}"}


def buscar_movimiento_banco(
    monto: float,
    tipo: str = "c2p",
    telefono: str = "",
    cedula: str = "",
    referencia: str = "",
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> Dict:
    """
    Función legacy — enruta al método correcto según tipo de pago.
    Para nuevos flujos usar validar_pago_fm() directamente.
    """
    tipo_lower = (tipo or "").lower()

    if "c2p" in tipo_lower or "movil" in tipo_lower or "pago_movil" in tipo_lower:
        return buscar_pago_c2p(monto, telefono, fecha_desde, fecha_hasta)
    elif "transfer" in tipo_lower or "cheque" in tipo_lower:
        return buscar_transferencia(monto, cedula, fecha_desde, fecha_hasta)
    elif "tarjeta" in tipo_lower or "tdd" in tipo_lower or "tdc" in tipo_lower:
        return buscar_pago_tarjeta(monto, referencia=referencia,
                                   fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)
    elif "efectivo" in tipo_lower:
        return {"confirmado": True, "tipo": "efectivo", "monto_confirmado": monto,
                "mensaje": "Efectivo — sin validación bancaria", "raw": None}
    else:
        result = buscar_pago_c2p(monto, telefono, fecha_desde, fecha_hasta)
        if not result.get("confirmado"):
            result = buscar_transferencia(monto, cedula, fecha_desde, fecha_hasta)
        return result



def _normalize_banco_response(data: Optional[Dict], tipo: str) -> Dict:
    """Normaliza la respuesta de Mercantil a un formato estándar."""
    if data is None:
        return {
            "confirmado": False,
            "tipo": tipo,
            "referencia_banco": "",
            "monto_confirmado": 0.0,
            "fecha_banco": "",
            "mensaje": "Sin respuesta del banco",
            "raw": None,
        }

    # Determinar si fue confirmado
    confirmado = False
    referencia = ""
    monto = 0.0
    fecha = ""
    mensaje = ""

    # Revisar campo de respuesta típico de Mercantil
    response_code = str(data.get("responseCode", data.get("response_code", data.get("code", "")))).strip()
    response_msg  = str(data.get("responseMessage", data.get("response_message", data.get("message", "")))).strip()

    # Códigos de éxito Mercantil: "00", "000", "approved"
    if response_code in ["00", "000", "0", "approved", "APPROVED", "success"]:
        confirmado = True
    elif "aprobad" in response_msg.lower() or "approved" in response_msg.lower():
        confirmado = True

    # Extraer referencia
    for key in ["referenceNumber", "reference_number", "reference", "nroReference", "trxId", "transaction_id"]:
        if key in data and data[key]:
            referencia = str(data[key])
            break

    # Extraer monto
    for key in ["amount", "monto", "valor"]:
        if key in data:
            try:
                monto = float(data[key])
                break
            except (TypeError, ValueError):
                pass

    # Extraer fecha
    for key in ["date", "fecha", "transactionDate", "transaction_date"]:
        if key in data:
            fecha = str(data[key])
            break

    mensaje = response_msg or f"Código: {response_code}"

    # Si hay lista de transacciones
    if "transactions" in data and isinstance(data["transactions"], list) and data["transactions"]:
        trx = data["transactions"][0]
        confirmado = True
        referencia = referencia or str(trx.get("reference", trx.get("referenceNumber", "")))
        monto = float(trx.get("amount", trx.get("monto", monto)) or monto)
        fecha = fecha or str(trx.get("date", trx.get("fecha", "")))

    return {
        "confirmado": confirmado,
        "tipo": tipo,
        "referencia_banco": referencia,
        "monto_confirmado": monto,
        "fecha_banco": fecha,
        "codigo_respuesta": response_code,
        "mensaje": mensaje,
        "raw": data,
    }
