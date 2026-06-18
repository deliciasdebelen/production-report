"""
Servicio BNC — Banco Nacional de Crédito (código 0191)
API: Api Soluciones en Línea v2.1
Doc: https://documenter.getpostman.com/view/37111270/2sAYBRFtg4

════ Ambiente DEV ════════════════════════════════════════════
  Base URL   : https://servicios.bncenlinea.com:16500/api
  Verificar  : GET  /welcome/home
  ClientGUID : ce7c95ff-2eac-4464-ad84-1330b31fb3b1   (DEV)
  MasterKey  : 980f5e8f83e51312f476b8819eccf3e8         (DEV)
  Cuenta     : 0191-0098-71-2198417249
  Teléfono PM: 584241321019 (0424-1321019 + código país)

════ Endpoints (todos POST, Content-Type: application/json) ═
  Auth
    Logon             POST /auth/logon

  Pago Móvil (P2P)
    Emisión P2P       POST /p2p/SendP2P
    Reverso P2P       (no aplica en consulta)

  VPOS / C2P
    Emisión C2P       POST /c2p/SendC2P
    Reverso C2P       POST /c2p/ReverseC2P

  Validaciones (consulta de pagos recibidos) — las más importantes para CXC
    Query P2P c/ref   POST /validation/QueryP2PMovement
    Query P2P s/ref   POST /validation/QueryP2PMovementWithoutReference
    Query Transacción POST /validation/QueryMovement
    Estatus SIMF      POST /operation/StatusOperation

  Cuenta
    Balance           POST /account/GetBalance
    Movimientos       POST /account/GetStatement

════ Encriptación ══════════════════════════════════════════
  PBKDF2(key, salt_ivan_medvedev, iterations=1000, SHA1) → 48 bytes
  Key = primeros 32 bytes;  IV = siguientes 16 bytes
  Cifrado: AES-256-CBC, plaintext en UTF-16-LE, padding PKCS7
  Logon encripta con MasterKey; resto con WorkingKey diaria.

════ Formato Request ═══════════════════════════════════════
  {
    "ClientGUID":      "<UUID>",
    "Reference":       "<id único del día, alfanumérico, ≤20c>",
    "Value":           "<payload JSON → AES → base64>",
    "Validation":      "<payload JSON → SHA-256 hex>",
    "swTestOperation": false
  }

════ Formato Respuesta ═════════════════════════════════════
  { "status": "OK|KO", "message": "<6-char-code><desc>",
    "value": "<resultado AES base64>", "validation": "<sha256>" }
  → Desencriptar "value" con la misma clave usada en la petición.
  → Si message contiene "RWK" → renovar WorkingKey.
"""
import os
import json
import hashlib
import logging
import uuid
import base64
from typing import Optional, Dict, Any, List
from datetime import date, datetime

import requests as _requests

logger = logging.getLogger(__name__)

# ═══ Configuración ════════════════════════════════════════════
BNC_BASE_URL    = os.getenv("BNC_API_URL",    "https://servicios.bncenlinea.com:16500/api")
BNC_CLIENT_GUID = os.getenv("BNC_CLIENT_GUID", "")
BNC_MASTER_KEY  = os.getenv("BNC_MASTER_KEY",  "")
BNC_TIMEOUT     = 20

# Cuenta y teléfono del comercio (para consultas de movimientos)
BNC_ACCOUNT_NUMBER = os.getenv("BNC_ACCOUNT_NUMBER", "01910098712198417249")  # 20 dígitos
BNC_PHONE_NUMBER   = os.getenv("BNC_PHONE_NUMBER",   "584241321019")           # con código país
BNC_CLIENT_ID      = os.getenv("BNC_CLIENT_ID",      "")                       # RIF empresa (J...)
BNC_BANK_CODE      = 191


def _cargar_config_desde_bd() -> bool:
    """
    Carga las credenciales BNC desde la tabla bancos_configuracion.
    Se usa como fallback cuando las variables de entorno no están configuradas.
    Retorna True si se cargaron credenciales válidas.
    """
    global BNC_BASE_URL, BNC_CLIENT_GUID, BNC_MASTER_KEY
    global BNC_ACCOUNT_NUMBER, BNC_PHONE_NUMBER, BNC_CLIENT_ID

    if BNC_CLIENT_GUID and BNC_MASTER_KEY:
        return True  # Ya están configuradas por env vars

    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        return False

    try:
        if "postgresql" in db_url or "postgres" in db_url:
            import psycopg2, psycopg2.extras
            from urllib.parse import urlparse
            u = urlparse(db_url)
            conn = psycopg2.connect(
                host=u.hostname, port=u.port or 5432,
                dbname=u.path.lstrip("/"), user=u.username, password=u.password,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
        else:
            import sqlite3
            conn = sqlite3.connect("/app/production.db")
            conn.row_factory = sqlite3.Row

        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM bancos_configuracion WHERE codigo_banco=%s AND activo=1",
            ("0191",)
        ) if "psycopg2" in str(type(conn)) else \
        cur.execute(
            "SELECT * FROM bancos_configuracion WHERE codigo_banco=? AND activo=1",
            ("0191",)
        )
        row = cur.fetchone()
        conn.close()

        if not row:
            return False

        row = dict(row)
        if row.get("client_guid"):
            BNC_CLIENT_GUID = row["client_guid"]
        if row.get("master_key"):
            BNC_MASTER_KEY  = row["master_key"]
        if row.get("base_url"):
            BNC_BASE_URL    = row["base_url"]
        if row.get("account_number"):
            BNC_ACCOUNT_NUMBER = row["account_number"]
        if row.get("phone_number"):
            BNC_PHONE_NUMBER   = row["phone_number"]
        if row.get("client_id"):
            BNC_CLIENT_ID      = row["client_id"]

        logger.info(f"BNC: credenciales cargadas desde BD para {row.get('nombre_banco','BNC')}")
        return bool(BNC_CLIENT_GUID and BNC_MASTER_KEY)

    except Exception as e:
        logger.debug(f"BNC: no se pudo cargar config desde BD: {e}")
        return False


# Intentar cargar desde BD si las env vars no están presentes
if not BNC_CLIENT_GUID or not BNC_MASTER_KEY:
    _cargar_config_desde_bd()


# WorkingKey diaria (cache en memoria; producción usa Redis)
_working_key_cache: Dict[str, str] = {}

# Salt fijo: "Ivan Medvedev" en ASCII hex
SALT_BYTES = bytes([0x49, 0x76, 0x61, 0x6e, 0x20, 0x4d, 0x65,
                    0x64, 0x76, 0x65, 0x64, 0x65, 0x76])

# ═══ Endpoints reales (base = /api) ══════════════════════════
# Auth
EP_LOGON               = "/auth/logon"
EP_WELCOME             = "/welcome/home"
# Pagos enviados
EP_P2P_SEND            = "/Transaction/Send"
EP_C2P_SEND            = "/Transaction/Send"
EP_C2P_REVERSE         = "/c2p/ReverseC2P"
# Validaciones de pagos recibidos
EP_QUERY_P2P           = "/Position/ValidateP2P"             # P2P con referencia
EP_QUERY_P2P_NREF      = "/Position/ValidateExistence"       # P2P sin referencia
EP_QUERY_TRANS         = "/Position/Validate"                # transferencia/genérica
EP_SIMF_STATUS         = "/operation/StatusOperation"
# Consultas de cuenta
EP_BALANCE             = "/Position/Current"                 # saldo
EP_FULL_BALANCE        = "/Position/FullBalance"             # saldo completo
EP_HISTORY             = "/Position/History"                 # últimos 3 días
EP_HISTORY_BY_DATE     = "/Position/HistoryByDate"           # rango (máx 31 días)
EP_HISTORY_DAILY       = "/Position/DailyTransactionHistory" # un día específico
EP_HISTORY_BY_CONTROL  = "/Position/GetDayTransactionsByControlNumber"  # por N° control
EP_STATEMENT           = EP_HISTORY_BY_DATE                  # alias compatibilidad


# ═══ Criptografía ═════════════════════════════════════════════

def _derive_key_iv(secret: str) -> tuple:
    """
    PBKDF2(secret_utf16le, SALT, iterations=1000, SHA1) → 48 bytes
    Key = primeros 32 bytes, IV = siguientes 16 bytes.
    """
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA1(),
        length=48,
        salt=SALT_BYTES,
        iterations=1000,
        backend=default_backend(),
    )
    derived = kdf.derive(secret.encode("utf-16-le"))
    return derived[:32], derived[32:48]


def _encrypt_aes(plaintext: str, secret: str) -> str:
    """Encripta texto (UTF-16-LE) con AES-256-CBC → base64."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding as sym_padding
    from cryptography.hazmat.backends import default_backend

    key, iv = _derive_key_iv(secret)
    raw = plaintext.encode("utf-16-le")
    padder = sym_padding.PKCS7(128).padder()
    padded = padder.update(raw) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    enc = cipher.encryptor()
    return base64.b64encode(enc.update(padded) + enc.finalize()).decode("ascii")


def _decrypt_aes(cipherb64: str, secret: str) -> str:
    """Desencripta base64 AES-256-CBC → string UTF-16-LE."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding as sym_padding
    from cryptography.hazmat.backends import default_backend

    key, iv = _derive_key_iv(secret)
    encrypted = base64.b64decode(cipherb64)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    dec = cipher.decryptor()
    padded = dec.update(encrypted) + dec.finalize()
    unpadder = sym_padding.PKCS7(128).unpadder()
    raw = unpadder.update(padded) + unpadder.finalize()
    return raw.decode("utf-16-le")


def _sha256(plaintext: str) -> str:
    """SHA-256 hex del texto UTF-8."""
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def _build_request(value_payload: dict, secret: str, reference: str = "") -> dict:
    """
    Construye el objeto request completo según el formato BNC v2.1:
      { ClientGUID, Reference, Value(AES), Validation(SHA256), swTestOperation }
    """
    ref       = reference or uuid.uuid4().hex[:20]
    value_str = json.dumps(value_payload, separators=(",", ":"), ensure_ascii=False)
    return {
        "ClientGUID":      BNC_CLIENT_GUID,
        "Reference":       ref,
        "Value":           _encrypt_aes(value_str, secret),
        "Validation":      _sha256(value_str),
        "swTestOperation": False,
    }


# ═══ HTTP ═════════════════════════════════════════════════════

def _post(endpoint: str, payload: dict) -> Optional[dict]:
    url = BNC_BASE_URL.rstrip("/") + endpoint
    try:
        resp = _requests.post(
            url, json=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=BNC_TIMEOUT, verify=False,
        )
        return resp.json()
    except Exception as e:
        logger.error(f"BNC POST {endpoint} error: {e}")
        return None


def verificar_conexion() -> bool:
    """Verifica la conexión al ambiente BNC (GET /welcome/home)."""
    url = BNC_BASE_URL.rstrip("/") + EP_WELCOME
    try:
        r = _requests.get(url, timeout=10, verify=False)
        return r.status_code == 200
    except Exception as e:
        logger.error(f"BNC: fallo verificar conexión: {e}")
        return False


# ═══ Autenticación ════════════════════════════════════════════

def _get_working_key(force: bool = False) -> Optional[str]:
    """
    Obtiene la WorkingKey diaria mediante Logon.
    Renueva si es otro día o si force=True.
    Payload: { "ClientGUID": "<guid>" }  → cifrado con MasterKey
    """
    global _working_key_cache

    today = date.today().isoformat()
    if not force and _working_key_cache.get("fecha") == today:
        return _working_key_cache.get("key")

    if not BNC_CLIENT_GUID or not BNC_MASTER_KEY:
        logger.warning("BNC: BNC_CLIENT_GUID / BNC_MASTER_KEY no configurados")
        return None

    logon_payload = {"ClientGUID": BNC_CLIENT_GUID}
    ref           = f"logon{today.replace('-','')}"
    req_body      = _build_request(logon_payload, BNC_MASTER_KEY, reference=ref)
    resp          = _post(EP_LOGON, req_body)

    if not resp or resp.get("status", "").upper() != "OK":
        msg = (resp or {}).get("message", "sin respuesta")
        logger.error(f"BNC Logon fallido: {msg}")
        return None

    try:
        raw    = _decrypt_aes(resp["value"], BNC_MASTER_KEY)
        result = json.loads(raw)
        wk     = result.get("WorkingKey", "")
        if not wk:
            logger.error("BNC: WorkingKey vacía en respuesta Logon")
            return None
        _working_key_cache = {"fecha": today, "key": wk}
        logger.info(f"BNC: WorkingKey renovada para {today}")
        return wk
    except Exception as e:
        logger.error(f"BNC: error desencriptando WorkingKey: {e}")
        return None


def _get_wk_or_fail() -> Optional[str]:
    """Obtiene WorkingKey; si hay RWK solicitado la renueva automáticamente."""
    return _get_working_key()


# ═══ Consultas de movimientos recibidos (para CXC) ════════════

def consultar_p2p_con_referencia(
    referencia:    str,
    monto:         float,
    telefono_pag:  str  = "",   # teléfono del pagador con código país (584...)
    banco_pag:     int  = 0,    # código banco del pagador
    cedula_pag:    str  = "",   # documento pagador Ej: V12345678
    fecha:         str  = "",   # yyyy/M/dThh:mm:ss
) -> Dict[str, Any]:
    """
    Valida un Pago Móvil P2P recibido buscando por referencia.
    Endpoint: POST /validation/QueryP2PMovement
    Campos requeridos: AccountNumber, BankCode, PhoneNumber, ClientID,
                       Reference, RequestDate, Amount
    """
    wk = _get_working_key()
    if not wk:
        return _sin_credenciales("p2p")

    fecha_dt = fecha or datetime.now().strftime("%Y/%m/%dT%H:%M:%S")
    payload = {
        "AccountNumber": BNC_ACCOUNT_NUMBER,
        "BankCode":      banco_pag or BNC_BANK_CODE,
        "PhoneNumber":   telefono_pag or BNC_PHONE_NUMBER,
        "ClientID":      cedula_pag  or BNC_CLIENT_ID,
        "Reference":     int(referencia) if referencia.isdigit() else referencia,
        "RequestDate":   fecha_dt,
        "Amount":        round(float(monto), 2),
    }
    ref_id  = f"qp2p{referencia[:12]}"
    req     = _build_request(payload, wk, reference=ref_id)
    resp    = _post(EP_QUERY_P2P, req)
    return _parsear_movimiento(resp, wk, monto, "p2p", referencia)


def consultar_p2p_sin_referencia(
    monto:        float,
    telefono_pag: str = "",
    banco_pag:    int = 0,
    cedula_pag:   str = "",
    fecha:        str = "",
) -> Dict[str, Any]:
    """
    Consulta Pago Móvil P2P recibido sin número de referencia.
    Endpoint: POST /validation/QueryP2PMovementWithoutReference
    """
    wk = _get_working_key()
    if not wk:
        return _sin_credenciales("p2p")

    fecha_dt = fecha or datetime.now().strftime("%Y/%m/%dT%H:%M:%S")
    payload = {
        "AccountNumber": BNC_ACCOUNT_NUMBER,
        "Amount":        round(float(monto), 2),
        "BankCode":      banco_pag or BNC_BANK_CODE,
        "ClientID":      cedula_pag or BNC_CLIENT_ID,
        "PhoneNumber":   telefono_pag or BNC_PHONE_NUMBER,
        "RequestDate":   fecha_dt,
    }
    ref_id = f"qp2nf{abs(hash(str(monto)+fecha_dt))%100000}"
    req    = _build_request(payload, wk, reference=ref_id)
    resp   = _post(EP_QUERY_P2P_NREF, req)
    return _parsear_movimiento(resp, wk, monto, "p2p_sin_ref", "")


def consultar_transferencia(
    referencia:    str,
    monto:         float,
    fecha_movim:   str = "",    # yyyy/MM/ddThh:mm:ss
    cedula_clie:   str = "",
) -> Dict[str, Any]:
    """
    Consulta una transferencia o depósito recibido por referencia.
    Endpoint: POST /validation/QueryMovement
    Campos: AccountNumber, Amount, ClientID, Reference, DateMovement
    """
    wk = _get_working_key()
    if not wk:
        return _sin_credenciales("transferencia")

    fecha_dt = fecha_movim or datetime.now().strftime("%Y/%m/%dT%H:%M:%S")
    payload = {
        "AccountNumber": BNC_ACCOUNT_NUMBER,
        "Amount":        round(float(monto), 2),
        "ClientID":      cedula_clie or BNC_CLIENT_ID,
        "Reference":     int(referencia) if referencia.isdigit() else referencia,
        "DateMovement":  fecha_dt,
    }
    ref_id = f"qtrf{referencia[:14]}"
    req    = _build_request(payload, wk, reference=ref_id)
    resp   = _post(EP_QUERY_TRANS, req)
    return _parsear_movimiento(resp, wk, monto, "transferencia", referencia)


def consultar_balance() -> Dict[str, Any]:
    """
    Consulta el balance de la cuenta BNC.
    Endpoint: POST /account/GetBalance
    """
    wk = _get_working_key()
    if not wk:
        return _sin_credenciales("balance")

    payload = {"AccountNumber": BNC_ACCOUNT_NUMBER}
    req     = _build_request(payload, wk, reference=f"bal{date.today().strftime('%Y%m%d')}")
    resp    = _post(EP_BALANCE, req)
    if not resp or resp.get("status", "").upper() != "OK":
        return {"status": "error", "message": (resp or {}).get("message", "Sin respuesta")}
    try:
        data = json.loads(_decrypt_aes(resp["value"], wk))
        return {"status": "ok", "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def obtener_historial(
    client_id:      str  = "",
    account_number: str  = "",
) -> Dict[str, Any]:
    """
    Obtiene el historial de los últimos 3 días.
    Endpoint: POST /Position/History
    Retorna lista de movimientos normalizados.
    """
    wk = _get_working_key()
    if not wk:
        return _sin_credenciales("historial")

    payload = {
        "ClientID":      client_id      or BNC_CLIENT_ID,
        "AccountNumber": account_number or BNC_ACCOUNT_NUMBER,
        "ChildClientID": "",
        "BranchID":      "",
    }
    ref_id = f"hist{date.today().strftime('%Y%m%d')}"
    req    = _build_request(payload, wk, reference=ref_id)
    resp   = _post(EP_HISTORY, req)
    return _procesar_historial(resp, wk, "historial_3dias")


def obtener_historial_por_fecha(
    desde:          str,       # yyyy-MM-dd
    hasta:          str,       # yyyy-MM-dd  (máx 31 días de rango)
    client_id:      str = "",
    account_number: str = "",
) -> Dict[str, Any]:
    """
    Obtiene historial por rango de fechas (máximo 31 días).
    Endpoint: POST /Position/HistoryByDate
    """
    wk = _get_working_key()
    if not wk:
        return _sin_credenciales("historial")

    payload = {
        "ClientID":      client_id      or BNC_CLIENT_ID,
        "AccountNumber": account_number or BNC_ACCOUNT_NUMBER,
        "StartDate":     desde,
        "EndDate":       hasta,
        "ChildClientID": "",
        "BranchID":      "",
    }
    ref_id = f"hbd{desde.replace('-','')}{hasta.replace('-','')}"
    req    = _build_request(payload, wk, reference=ref_id)
    resp   = _post(EP_HISTORY_BY_DATE, req)
    return _procesar_historial(resp, wk, "historial_por_fecha")


def obtener_historial_diario(
    fecha:          str,       # yyyy-MM-dd
    client_id:      str = "",
    account_number: str = "",
) -> Dict[str, Any]:
    """
    Obtiene historial de un día específico (días anteriores).
    Endpoint: POST /Position/DailyTransactionHistory
    """
    wk = _get_working_key()
    if not wk:
        return _sin_credenciales("historial")

    payload = {
        "ClientID":      client_id      or BNC_CLIENT_ID,
        "AccountNumber": account_number or BNC_ACCOUNT_NUMBER,
        "Date":          fecha,
        "ChildClientID": "",
        "BranchID":      "",
    }
    ref_id = f"hdy{fecha.replace('-','')}"
    req    = _build_request(payload, wk, reference=ref_id)
    resp   = _post(EP_HISTORY_DAILY, req)
    return _procesar_historial(resp, wk, "historial_diario")


def consultar_movimientos(
    desde: str,
    hasta: str,
    page:  int = 1,
    per_page: int = 50,
) -> Dict[str, Any]:
    """Alias de obtener_historial_por_fecha (compatibilidad)."""
    return obtener_historial_por_fecha(desde=desde, hasta=hasta)


def _procesar_historial(resp: Optional[dict], wk: str, origen: str) -> Dict[str, Any]:
    """
    Desencripta la respuesta de los endpoints /Position/History*
    y normaliza los movimientos a formato estándar CXC.
    Respuesta BNC: dict { "<cuenta>-<fecha>": [ { movimiento }, ... ] }
    """
    if not resp:
        return {"status": "error", "message": "Sin respuesta del servidor BNC"}

    status  = resp.get("status", "KO").upper()
    message = resp.get("message", "")

    if "RWK" in message:
        logger.info("BNC: Renovando WorkingKey (RWK solicitado)")
        _get_working_key(force=True)

    if status != "OK":
        return {"status": "error", "message": message}

    try:
        raw  = _decrypt_aes(resp["value"], wk)
        data = json.loads(raw)
        movimientos = _normalizar_movimientos(data)
        return {
            "status":       "ok",
            "origen":       origen,
            "total":        len(movimientos),
            "data":         data,          # respuesta raw desencriptada
            "movimientos":  movimientos,   # lista normalizada
        }
    except Exception as e:
        logger.error(f"BNC historial: error desencriptando: {e}")
        return {"status": "error", "message": str(e)}


def _normalizar_movimientos(data: Any) -> List[Dict[str, Any]]:
    """
    Convierte la respuesta del historial BNC (dict o lista) en una lista
    homogénea de movimientos con campos estándar para CXC.
    Campos de entrada BNC:
      Date, ControlNumber, Amount, Code, DebtorInstrument, Concept,
      BankCode, Type, BalanceDelta, ReferenceA, ReferenceB, ReferenceC, ReferenceD
    """
    result = []

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        # BNC devuelve { "<key>": [ movimientos ] } — aplanar todas las listas
        items = []
        for v in data.values():
            if isinstance(v, list):
                items.extend(v)
            elif isinstance(v, dict):
                items.append(v)
    else:
        return result

    for m in items:
        if not isinstance(m, dict):
            continue

        balance_delta = str(m.get("BalanceDelta", "")).upper()
        tipo_mov      = "credito" if balance_delta in ("C", "CRE", "CR", "+") else "debito"
        banco_code    = str(m.get("BankCode", "0")).zfill(4)
        monto         = float(m.get("Amount", 0) or 0)

        # Determinar tipo de pago según Code / Type / DebtorInstrument
        code            = str(m.get("Code", "")).upper()
        debtor_inst     = str(m.get("DebtorInstrument", "")).upper()
        tipo_transaccion = "transferencia"
        if "P2P" in code or "PM" in debtor_inst or "PAGO MOVIL" in debtor_inst:
            tipo_transaccion = "pago_movil"
        elif "C2P" in code or "COBRO" in code:
            tipo_transaccion = "c2p"
        elif "POS" in code or "TARJ" in debtor_inst:
            tipo_transaccion = "tarjeta"

        result.append({
            "fecha":            m.get("Date", ""),
            "control_number":   str(m.get("ControlNumber", "")),
            "monto":            monto,
            "code":             m.get("Code", ""),
            "tipo_movimiento":  tipo_mov,
            "tipo_pago":        tipo_transaccion,
            "banco_origen":     banco_code,
            "concepto":         m.get("Concept", ""),
            "referencia_a":     str(m.get("ReferenceA", "")),
            "referencia_b":     str(m.get("ReferenceB", "")),
            "referencia_c":     str(m.get("ReferenceC", "")),
            "referencia_d":     str(m.get("ReferenceD", "")),
            "debtor_instrument": m.get("DebtorInstrument", ""),
            "debtor_id":        m.get("DebtorID", ""),
            "debtor_type":      m.get("DebtorType", ""),
            "balance_delta":    balance_delta,
            "raw":              m,
        })

    return result


def consultar_estatus_simf(referencia: str, tipo: str = "CRE") -> Dict[str, Any]:
    """
    Consulta el estatus de una operación SIMF (transferencia interbancaria).
    Endpoint: POST /operation/StatusOperation
    Campos: OperationType ("DEB"|"CRE"|"REV"), Reference
    """
    wk = _get_working_key()
    if not wk:
        return _sin_credenciales("simf")

    payload = {
        "OperationType": tipo,
        "ClientID":      BNC_CLIENT_ID or BNC_CLIENT_GUID,
        "Reference":     referencia,
    }
    ref_id = f"simf{referencia[:14]}"
    req    = _build_request(payload, wk, reference=ref_id)
    resp   = _post(EP_SIMF_STATUS, req)
    if not resp or resp.get("status", "").upper() != "OK":
        return {"status": "error", "message": (resp or {}).get("message", "Sin respuesta")}
    try:
        data = json.loads(_decrypt_aes(resp["value"], wk))
        return {"status": "ok", "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ═══ Función principal de validación (usada por conciliación CXC) ══

def validar_pago_bnc(
    referencia:   str,
    monto:        float,
    tipo:         str  = "p2p",   # p2p | transferencia | deposito
    telefono:     str  = "",
    cedula:       str  = "",
    banco_origen: str  = "",
    fecha:        str  = "",
) -> Dict[str, Any]:
    """
    Valida un pago recibido en BNC según el tipo.
    Retorna dict estándar: { confirmado, monto_confirmado, tipo, banco, mensaje, detalle }
    """
    tipo_lower = tipo.lower()

    if tipo_lower in ("p2p", "pago_movil", "pm", "movil"):
        if referencia:
            return consultar_p2p_con_referencia(
                referencia=referencia, monto=monto,
                telefono_pag=telefono, cedula_pag=cedula,
                banco_pag=int(banco_origen) if banco_origen.isdigit() else 0,
                fecha=fecha,
            )
        else:
            return consultar_p2p_sin_referencia(
                monto=monto, telefono_pag=telefono,
                cedula_pag=cedula,
                banco_pag=int(banco_origen) if banco_origen.isdigit() else 0,
                fecha=fecha,
            )

    if tipo_lower in ("transferencia", "trf", "deposito", "dep"):
        return consultar_transferencia(
            referencia=referencia, monto=monto,
            cedula_clie=cedula, fecha_movim=fecha,
        )

    # Fallback: intentar consulta de transferencia
    return consultar_transferencia(referencia=referencia, monto=monto, fecha_movim=fecha)


# Alias para compatibilidad con código existente
def buscar_pago_movil_bnc(referencia, monto, telefono="", fecha=""):
    return consultar_p2p_con_referencia(referencia, monto, telefono_pag=telefono, fecha=fecha)

def buscar_transferencia_bnc(referencia, monto, fecha=""):
    return consultar_transferencia(referencia, monto, fecha_movim=fecha)

def buscar_c2p_bnc(referencia, monto, telefono="", fecha=""):
    return consultar_p2p_con_referencia(referencia, monto, telefono_pag=telefono, fecha=fecha)


# ═══ Parseo de respuestas ══════════════════════════════════════

def _parsear_movimiento(
    resp:          Optional[dict],
    wk:            str,
    monto_esperado: float,
    tipo:          str,
    referencia:    str,
) -> Dict[str, Any]:
    """
    Desencripta el Value de la respuesta BNC y evalúa si la transacción confirmó.
    Campos respuesta: MovementExists, Date, ControlNumber, Amount, BankCode,
                      Code, DebtorInstrument, Concept, DebitAccount, Type,
                      BalanceDelta, ReferenceA..D, DebtorID, DebtorType
    """
    base = {"tipo": tipo, "banco": "BNC", "codigo_banco": "0191", "referencia": referencia}

    if not resp:
        return {**base, "confirmado": False, "monto_confirmado": 0,
                "mensaje": "Sin respuesta del servidor BNC"}

    status  = resp.get("status", "KO").upper()
    message = resp.get("message", "")

    # Renovar WorkingKey si el banco lo solicita
    if "RWK" in message:
        logger.info("BNC: Renovando WorkingKey (RWK solicitado)")
        _get_working_key(force=True)

    if status != "OK":
        return {**base, "confirmado": False, "monto_confirmado": 0, "mensaje": message}

    try:
        raw  = _decrypt_aes(resp["value"], wk)
        data = json.loads(raw)

        existe          = data.get("MovementExists", False)
        monto_banco     = float(data.get("Amount", data.get("amount", 0)) or 0)
        balance_delta   = data.get("BalanceDelta", "")
        control_number  = data.get("ControlNumber", "")
        ref_a           = data.get("ReferenceA", "")
        debtor_id       = data.get("DebtorID", "")
        debtor_type     = data.get("DebtorType", "")

        # Un crédito (ingreso) en balance_delta indica que el pago fue recibido
        es_credito = balance_delta.upper() in ("C", "CRE", "CREDITO", "CRÉDITO", "+", "CR")

        confirmado = (
            existe and
            es_credito and
            abs(monto_banco - monto_esperado) < max(1.0, monto_esperado * 0.01)
        )

        return {
            **base,
            "confirmado":       confirmado,
            "monto_confirmado": monto_banco,
            "mensaje":          message or ("Pago confirmado" if confirmado else "Movimiento no confirmado"),
            "control_number":   control_number,
            "ref_banco":        ref_a,
            "movement_exists":  existe,
            "balance_delta":    balance_delta,
            "debtor_id":        debtor_id,
            "debtor_type":      debtor_type,
            "detalle":          data,
        }
    except Exception as e:
        logger.error(f"BNC: error desencriptando respuesta movimiento: {e}")
        return {**base, "confirmado": False, "monto_confirmado": 0,
                "mensaje": f"Error al procesar respuesta: {e}"}


# ═══ Helpers ══════════════════════════════════════════════════

def _sin_credenciales(tipo: str = "desconocido") -> Dict[str, Any]:
    return {
        "confirmado":       False,
        "monto_confirmado": 0,
        "tipo":             tipo,
        "banco":            "BNC",
        "codigo_banco":     "0191",
        "mensaje":          "Credenciales BNC no configuradas (BNC_CLIENT_GUID / BNC_MASTER_KEY)",
        "referencia":       "",
    }


def bnc_disponible() -> bool:
    """True si las credenciales están configuradas."""
    return bool(BNC_CLIENT_GUID and BNC_MASTER_KEY)


def obtener_info_config() -> Dict[str, Any]:
    """Retorna la configuración actual del servicio (sin exponer claves sensibles)."""
    return {
        "base_url":        BNC_BASE_URL,
        "client_guid":     BNC_CLIENT_GUID[:8] + "..." if BNC_CLIENT_GUID else "",
        "master_key_set":  bool(BNC_MASTER_KEY),
        "account_number":  BNC_ACCOUNT_NUMBER,
        "phone_number":    BNC_PHONE_NUMBER,
        "client_id":       BNC_CLIENT_ID,
        "bank_code":       BNC_BANK_CODE,
        "disponible":      bnc_disponible(),
        "wk_cache_date":   _working_key_cache.get("fecha", ""),
        "endpoints": {
            "auth_logon":       EP_LOGON,
            "p2p_send":         EP_P2P_SEND,
            "c2p_send":         EP_C2P_SEND,
            "query_p2p":        EP_QUERY_P2P,
            "query_p2p_noref":  EP_QUERY_P2P_NREF,
            "query_transfer":   EP_QUERY_TRANS,
            "simf_status":      EP_SIMF_STATUS,
            "balance":          EP_BALANCE,
            "statement":        EP_STATEMENT,
        }
    }
