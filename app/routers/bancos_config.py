"""
Router: Configuración de Bancos para Conciliación CXC
Tabla: bancos_configuracion
URL prefix: /administracion/cxc/api/bancos
"""
from fastapi import APIRouter, Depends, Body, Path, Query
from fastapi.responses import JSONResponse
from app.dependencies import get_current_user
from app import models
from typing import Optional
import logging, sqlite3, os, json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/administracion/cxc/api/bancos", tags=["bancos-config"])

# ── Tipos de API soportados ──────────────────────────────
TIPOS_API = {
    "bnc":       "BNC (Rijndael + SHA-256)",
    "mercantil": "Mercantil (OAuth2)",
    "bnv":       "Banco de Venezuela (BDV)",
    "banesco":   "Banesco Open API",
    "rest":      "REST genérico (Bearer/API-Key)",
    "soap":      "SOAP/WSDL",
    "custom":    "Personalizado",
}

CAMPOS_CREDENCIAL = {
    "bnc":       ["client_guid", "master_key"],
    "mercantil": ["client_guid", "api_key", "api_secret"],
    "bnv":       ["username_api", "password_api", "api_key"],
    "banesco":   ["client_guid", "api_key", "api_secret"],
    "rest":      ["api_key", "api_secret", "username_api", "password_api"],
    "soap":      ["username_api", "password_api", "api_key"],
    "custom":    ["client_guid", "api_key", "api_secret", "username_api",
                  "password_api", "master_key"],
}


def _get_conn():
    """Retorna (conn, is_pg). Para PostgreSQL usa RealDictCursor para que dict(row) funcione."""
    db_url = os.getenv("DATABASE_URL", "")
    is_pg  = "postgresql" in db_url or "postgres" in db_url
    if is_pg:
        import psycopg2, psycopg2.extras
        from urllib.parse import urlparse
        u    = urlparse(db_url)
        conn = psycopg2.connect(
            host=u.hostname, port=u.port or 5432,
            dbname=u.path.lstrip("/"), user=u.username, password=u.password,
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        return conn, True
    conn = sqlite3.connect("/app/production.db")
    conn.row_factory = sqlite3.Row
    return conn, False


def _ph(is_pg: bool) -> str:
    """Placeholder SQL: %s para PG, ? para SQLite."""
    return "%s" if is_pg else "?"


def _mask(val: str) -> str:
    """Enmascara credenciales para la UI."""
    if not val:
        return ""
    if len(val) <= 6:
        return "●" * len(val)
    return val[:3] + "●" * (len(val) - 6) + val[-3:]


def _es_admin(user: models.User) -> bool:
    """True si el usuario es Admin (role=4) o tiene extra_role 4."""
    if user is None:
        return False
    if user.role == 4:
        return True
    try:
        return any(getattr(ur, 'role_id', None) == 4 for ur in (user.extra_roles or []))
    except Exception:
        return False


def _require_admin(user: models.User) -> Optional[JSONResponse]:
    """Devuelve JSONResponse 403 si no es admin, None si puede continuar."""
    if not _es_admin(user):
        return JSONResponse(status_code=403, content={
            "status": "forbidden",
            "message": "Solo administradores pueden acceder a esta función."
        })
    return None


def _migrate_cuentas():
    """Crea la tabla bancos_cuentas si no existe (migración auto en startup)."""
    try:
        conn, is_pg = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bancos_cuentas (
                id             SERIAL PRIMARY KEY,
                banco_id       INTEGER NOT NULL,
                numero_cuenta  TEXT NOT NULL,
                tipo_cuenta    TEXT DEFAULT 'corriente',
                descripcion    TEXT,
                moneda         TEXT DEFAULT 'VES',
                activo         INTEGER DEFAULT 1,
                created_at     TIMESTAMP DEFAULT NOW()
            )
        """) if is_pg else cur.execute("""
            CREATE TABLE IF NOT EXISTS bancos_cuentas (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                banco_id       INTEGER NOT NULL,
                numero_cuenta  TEXT NOT NULL,
                tipo_cuenta    TEXT DEFAULT 'corriente',
                descripcion    TEXT,
                moneda         TEXT DEFAULT 'VES',
                activo         INTEGER DEFAULT 1,
                created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        logger.info("bancos_cuentas table ensured.")
    except Exception as e:
        logger.warning(f"_migrate_cuentas: {e}")


# Ejecutar migración al importar el módulo
try:
    _migrate_cuentas()
except Exception:
    pass


# ─────────────────────────────────────────────────────────
# GET /config  — listar todos
# ─────────────────────────────────────────────────────────
@router.get("/config")
async def listar_bancos_config(
    user: models.User = Depends(get_current_user)
):
    try:
        conn, is_pg = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id,codigo_banco,nombre_banco,activo,tipo_api,
                   base_url,auth_endpoint,transfer_endpoint,c2p_endpoint,
                   client_guid,master_key,api_key,api_secret,username_api,
                   account_number,phone_number,client_id,
                   query_p2p_endpoint,query_p2p_noref_endpoint,
                   query_trans_endpoint,simf_endpoint,
                   balance_endpoint,statement_endpoint,
                   notas,created_at,updated_at
            FROM bancos_configuracion
            ORDER BY nombre_banco
        """)
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            # Enmascarar credenciales sensibles en la respuesta
            d["master_key_masked"] = _mask(d.get("master_key") or "")
            d["api_key_masked"]    = _mask(d.get("api_key")    or "")
            d["api_secret_masked"] = _mask(d.get("api_secret") or "")
            # No enviar valores reales al frontend
            d.pop("master_key",  None)
            d.pop("api_key",     None)
            d.pop("api_secret",  None)
            d["campos_requeridos"] = CAMPOS_CREDENCIAL.get(d.get("tipo_api","rest"), [])
            d["tipo_api_label"]    = TIPOS_API.get(d.get("tipo_api","rest"), "REST")
            rows.append(d)
        conn.close()
        return {
            "status": "ok",
            "data": rows,
            "tipos_api": TIPOS_API,
            "campos_credencial": CAMPOS_CREDENCIAL,
        }
    except Exception as e:
        logger.error(f"listar bancos config: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# ─────────────────────────────────────────────────────────
# POST /config  — crear o actualizar (upsert por codigo_banco)
# ─────────────────────────────────────────────────────────
@router.post("/config")
async def guardar_banco_config(
    body: dict = Body(...),
    user: models.User = Depends(get_current_user)
):
    """
    Guarda (inserta o actualiza) la configuración de un banco.
    Si el campo de credencial viene vacío se conserva el valor previo.
    """
    try:
        codigo = str(body.get("codigo_banco", "")).strip().zfill(4)
        if not codigo or codigo == "0000":
            return JSONResponse(status_code=400,
                content={"status": "error", "message": "codigo_banco requerido"})

        nombre     = body.get("nombre_banco", f"Banco {codigo}").strip()
        activo     = 1 if body.get("activo", True) else 0
        tipo_api   = body.get("tipo_api", "rest").strip()
        base_url   = body.get("base_url", "").strip()
        auth_ep    = body.get("auth_endpoint", "").strip()
        trans_ep   = body.get("transfer_endpoint", "").strip()
        c2p_ep     = body.get("c2p_endpoint", "").strip()
        notas      = body.get("notas", "").strip()
        extra      = json.dumps(body.get("extra_config") or {})
        # Campos BNC específicos
        account_number        = body.get("account_number", "").strip() or None
        phone_number          = body.get("phone_number", "").strip() or None
        client_id             = body.get("client_id", "").strip() or None
        query_p2p_ep          = body.get("query_p2p_endpoint", "").strip() or None
        query_p2p_noref_ep    = body.get("query_p2p_noref_endpoint", "").strip() or None
        query_trans_ep        = body.get("query_trans_endpoint", "").strip() or None
        simf_ep               = body.get("simf_endpoint", "").strip() or None
        balance_ep            = body.get("balance_endpoint", "").strip() or None
        statement_ep          = body.get("statement_endpoint", "").strip() or None

        # Credenciales: solo actualizar si vienen no vacías
        client_guid  = body.get("client_guid", "").strip() or None
        master_key   = body.get("master_key",  "").strip() or None
        api_key      = body.get("api_key",     "").strip() or None
        api_secret   = body.get("api_secret",  "").strip() or None
        username_api = body.get("username_api","").strip() or None
        password_api = body.get("password_api","").strip() or None

        conn, is_pg = _get_conn()
        cur = conn.cursor()

        if is_pg:
            ph = "%s"
            cur.execute(f"""
                INSERT INTO bancos_configuracion
                    (codigo_banco,nombre_banco,activo,tipo_api,base_url,
                     auth_endpoint,transfer_endpoint,c2p_endpoint,
                     client_guid,master_key,api_key,api_secret,
                     username_api,password_api,extra_config,notas,
                     account_number,phone_number,client_id,
                     query_p2p_endpoint,query_p2p_noref_endpoint,
                     query_trans_endpoint,simf_endpoint,
                     balance_endpoint,statement_endpoint,
                     updated_at)
                VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},NOW())
                ON CONFLICT(codigo_banco) DO UPDATE SET
                    nombre_banco=EXCLUDED.nombre_banco,
                    activo=EXCLUDED.activo, tipo_api=EXCLUDED.tipo_api,
                    base_url=EXCLUDED.base_url,
                    auth_endpoint=EXCLUDED.auth_endpoint,
                    transfer_endpoint=EXCLUDED.transfer_endpoint,
                    c2p_endpoint=EXCLUDED.c2p_endpoint,
                    client_guid=COALESCE(EXCLUDED.client_guid, bancos_configuracion.client_guid),
                    master_key=COALESCE(EXCLUDED.master_key,   bancos_configuracion.master_key),
                    api_key=COALESCE(EXCLUDED.api_key,         bancos_configuracion.api_key),
                    api_secret=COALESCE(EXCLUDED.api_secret,   bancos_configuracion.api_secret),
                    username_api=COALESCE(EXCLUDED.username_api,bancos_configuracion.username_api),
                    password_api=COALESCE(EXCLUDED.password_api,bancos_configuracion.password_api),
                    extra_config=EXCLUDED.extra_config,
                    notas=EXCLUDED.notas,
                    account_number=COALESCE(EXCLUDED.account_number, bancos_configuracion.account_number),
                    phone_number=COALESCE(EXCLUDED.phone_number,     bancos_configuracion.phone_number),
                    client_id=COALESCE(EXCLUDED.client_id,           bancos_configuracion.client_id),
                    query_p2p_endpoint=COALESCE(EXCLUDED.query_p2p_endpoint, bancos_configuracion.query_p2p_endpoint),
                    query_p2p_noref_endpoint=COALESCE(EXCLUDED.query_p2p_noref_endpoint, bancos_configuracion.query_p2p_noref_endpoint),
                    query_trans_endpoint=COALESCE(EXCLUDED.query_trans_endpoint, bancos_configuracion.query_trans_endpoint),
                    simf_endpoint=COALESCE(EXCLUDED.simf_endpoint,   bancos_configuracion.simf_endpoint),
                    balance_endpoint=COALESCE(EXCLUDED.balance_endpoint, bancos_configuracion.balance_endpoint),
                    statement_endpoint=COALESCE(EXCLUDED.statement_endpoint, bancos_configuracion.statement_endpoint),
                    updated_at=NOW()
            """, (codigo,nombre,activo,tipo_api,base_url,
                  auth_ep,trans_ep,c2p_ep,
                  client_guid,master_key,api_key,api_secret,
                  username_api,password_api,extra,notas,
                  account_number,phone_number,client_id,
                  query_p2p_ep,query_p2p_noref_ep,query_trans_ep,
                  simf_ep,balance_ep,statement_ep))
        else:
            cur.execute("""
                INSERT INTO bancos_configuracion
                    (codigo_banco,nombre_banco,activo,tipo_api,base_url,
                     auth_endpoint,transfer_endpoint,c2p_endpoint,
                     client_guid,master_key,api_key,api_secret,
                     username_api,password_api,extra_config,notas,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
                ON CONFLICT(codigo_banco) DO UPDATE SET
                    nombre_banco=excluded.nombre_banco,
                    activo=excluded.activo, tipo_api=excluded.tipo_api,
                    base_url=excluded.base_url,
                    auth_endpoint=excluded.auth_endpoint,
                    transfer_endpoint=excluded.transfer_endpoint,
                    c2p_endpoint=excluded.c2p_endpoint,
                    client_guid=COALESCE(excluded.client_guid, bancos_configuracion.client_guid),
                    master_key=COALESCE(excluded.master_key,   bancos_configuracion.master_key),
                    api_key=COALESCE(excluded.api_key,         bancos_configuracion.api_key),
                    api_secret=COALESCE(excluded.api_secret,   bancos_configuracion.api_secret),
                    username_api=COALESCE(excluded.username_api,bancos_configuracion.username_api),
                    password_api=COALESCE(excluded.password_api,bancos_configuracion.password_api),
                    extra_config=excluded.extra_config,
                    notas=excluded.notas, updated_at=CURRENT_TIMESTAMP
            """, (codigo,nombre,activo,tipo_api,base_url,
                  auth_ep,trans_ep,c2p_ep,
                  client_guid,master_key,api_key,api_secret,
                  username_api,password_api,extra,notas))

        conn.commit()
        conn.close()

        # Limpiar caché del servicio de conciliación
        try:
            from app.services.banco_mercantil_service import _limpiar_cache_bancos
            _limpiar_cache_bancos()
        except Exception:
            pass

        return {"status": "ok", "codigo_banco": codigo, "nombre": nombre}

    except Exception as e:
        logger.error(f"guardar banco config: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# ─────────────────────────────────────────────────────────
# DELETE /config/{codigo}  — eliminar banco
# ─────────────────────────────────────────────────────────
@router.delete("/config/{codigo}")
async def eliminar_banco_config(
    codigo: str = Path(...),
    user: models.User = Depends(get_current_user)
):
    try:
        conn, _ = _get_conn()
        cur = conn.cursor()
        conn, is_pg = _get_conn()
        cur = conn.cursor()
        ph  = _ph(is_pg)
        cur.execute(f"DELETE FROM bancos_configuracion WHERE codigo_banco = {ph}", (codigo,))
        deleted = cur.rowcount
        conn.commit()
        conn.close()
        if not deleted:
            return JSONResponse(status_code=404,
                content={"status": "error", "message": f"Banco {codigo} no encontrado"})
        try:
            from app.services.banco_mercantil_service import _limpiar_cache_bancos
            _limpiar_cache_bancos()
        except Exception:
            pass
        return {"status": "ok", "eliminado": codigo}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# ─────────────────────────────────────────────────────────
# POST /config/{codigo}/test  — probar conexión
# ─────────────────────────────────────────────────────────
@router.post("/config/{codigo}/test")
async def test_banco_config(
    codigo: str = Path(...),
    user: models.User = Depends(get_current_user)
):
    """Prueba la conexión con el banco según su tipo de API configurado."""
    try:
        conn, is_pg = _get_conn()
        cur = conn.cursor()
        ph  = _ph(is_pg)
        cur.execute(f"SELECT * FROM bancos_configuracion WHERE codigo_banco = {ph}", (codigo,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return JSONResponse(status_code=404,
                content={"status": "error", "message": f"Banco {codigo} no configurado"})

        cfg = dict(row)
        tipo = cfg.get("tipo_api", "rest")

        if tipo == "bnc":
            from app.services.banco_bnc_service import bnc_disponible, _get_working_key
            import os
            # Configurar credenciales desde BD temporalmente
            if cfg.get("client_guid"): os.environ["BNC_CLIENT_GUID"] = cfg["client_guid"]
            if cfg.get("master_key"):  os.environ["BNC_MASTER_KEY"]  = cfg["master_key"]
            disp = bnc_disponible()
            if disp:
                key = _get_working_key(force=True)
                conectado = key is not None
                return {"status": "ok", "conectado": conectado,
                        "mensaje": "BNC autenticado correctamente" if conectado else "Error obteniendo working key BNC"}
            return {"status": "ok", "conectado": False,
                    "mensaje": "Faltan credenciales BNC (client_guid / master_key)"}

        # Para otros tipos: verificar URL base
        if cfg.get("base_url"):
            import requests
            try:
                r = requests.get(cfg["base_url"], timeout=8)
                return {"status": "ok", "conectado": r.status_code < 500,
                        "http_code": r.status_code,
                        "mensaje": f"URL responde HTTP {r.status_code}"}
            except Exception as e:
                return {"status": "ok", "conectado": False, "mensaje": str(e)}

        return {"status": "ok", "conectado": False,
                "mensaje": "Configure base_url para probar la conexión"}

    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# ─────────────────────────────────────────────────────────
# GET /tipos  — lista de tipos de API disponibles
# ─────────────────────────────────────────────────────────
@router.get("/tipos")
async def listar_tipos_api(user: models.User = Depends(get_current_user)):
    return {"status": "ok", "tipos": TIPOS_API, "campos": CAMPOS_CREDENCIAL}


# ─────────────────────────────────────────────────────────
# POST /test  — probar conexión con payload directo (antes de guardar)
# ─────────────────────────────────────────────────────────
@router.post("/test")
async def test_banco_payload(
    payload: dict = Body(...),
    user: models.User = Depends(get_current_user),
):
    """Prueba la conexión usando los datos del formulario (sin necesidad de guardar primero)."""
    try:
        tipo     = payload.get("tipo_api", "rest")
        base_url = payload.get("base_url", "").strip()

        if tipo == "bnc":
            client_guid = payload.get("client_guid", "").strip()
            master_key  = payload.get("master_key",  "").strip()
            if not client_guid or not master_key:
                return {"status": "error",
                        "message": "Se requieren ClientGUID y MasterKey para BNC"}
            import os
            os.environ["BNC_CLIENT_GUID"] = client_guid
            os.environ["BNC_MASTER_KEY"]  = master_key
            os.environ["BNC_API_URL"]     = (base_url or "https://servicios.bncenlinea.com:16500/api")
            import importlib
            import app.services.banco_bnc_service as bnc_svc
            bnc_svc.BNC_CLIENT_GUID = client_guid
            bnc_svc.BNC_MASTER_KEY  = master_key
            bnc_svc.BNC_BASE_URL    = os.environ["BNC_API_URL"]
            wk = bnc_svc._get_working_key(force=True)
            if wk:
                return {"status": "ok",
                        "message": f"BNC autenticado correctamente — WorkingKey obtenida"}
            return {"status": "error",
                    "message": "BNC: no se pudo obtener WorkingKey (verifique credenciales y conectividad)"}

        if base_url:
            import requests
            try:
                r = requests.get(base_url, timeout=8, verify=False)
                return {"status": "ok",
                        "message": f"URL responde HTTP {r.status_code}",
                        "http_code": r.status_code}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        return {"status": "error", "message": "Configure la URL base para probar la conexión"}

    except Exception as e:
        logger.error(f"test_banco_payload error: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# ─────────────────────────────────────────────────────────
# CONSULTAS BANCARIAS EN TIEMPO REAL
# GET /{codigo}/saldo          — saldo de la cuenta
# GET /{codigo}/historial      — últimos 3 días
# GET /{codigo}/historial-fecha — rango de fechas (máx 31 días)
# GET /{codigo}/pago-movil     — validar pago móvil
# ─────────────────────────────────────────────────────────

def _cargar_banco_cfg(codigo: str) -> dict:
    """Carga la configuración de un banco desde BD y la retorna como dict."""
    conn, is_pg = _get_conn()
    ph = _ph(is_pg)
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM bancos_configuracion WHERE codigo_banco={ph} AND activo=1", (codigo,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else {}


def _init_bnc_svc_from_cfg(cfg: dict):
    """Configura el módulo BNC con las credenciales del registro de BD."""
    import app.services.banco_bnc_service as svc
    if cfg.get("client_guid"):   svc.BNC_CLIENT_GUID    = cfg["client_guid"]
    if cfg.get("master_key"):    svc.BNC_MASTER_KEY     = cfg["master_key"]
    if cfg.get("base_url"):      svc.BNC_BASE_URL        = cfg["base_url"]
    if cfg.get("account_number"):svc.BNC_ACCOUNT_NUMBER  = cfg["account_number"]
    if cfg.get("phone_number"):  svc.BNC_PHONE_NUMBER    = cfg["phone_number"]
    if cfg.get("client_id"):     svc.BNC_CLIENT_ID       = cfg["client_id"]
    # Forzar renovación de WorkingKey al cambiar credenciales
    svc._working_key_cache = {}
    return svc


@router.get("/{codigo}/saldo")
async def consultar_saldo_banco(
    codigo: str = Path(..., description="Código banco (4 dígitos, ej: 0191)"),
    user: models.User = Depends(get_current_user),
):
    """Consulta el saldo actual de la cuenta bancaria configurada."""
    try:
        cfg = _cargar_banco_cfg(codigo)
        if not cfg:
            return JSONResponse(status_code=404, content={
                "status": "error",
                "message": f"Banco {codigo} no configurado o no activo"})

        tipo = cfg.get("tipo_api", "")
        if tipo != "bnc":
            return JSONResponse(status_code=400, content={
                "status": "error",
                "message": f"Consulta de saldo no implementada para tipo '{tipo}'"})

        svc  = _init_bnc_svc_from_cfg(cfg)
        res  = svc.consultar_balance()
        return {
            "status":       res.get("status", "error"),
            "banco":        cfg.get("nombre_banco", codigo),
            "codigo_banco": codigo,
            "cuenta":       cfg.get("account_number", ""),
            "data":         res.get("data"),
            "message":      res.get("message", ""),
        }
    except Exception as e:
        logger.error(f"consultar_saldo_banco {codigo}: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/{codigo}/historial")
async def consultar_historial_banco(
    codigo: str = Path(..., description="Código banco 4 dígitos"),
    user: models.User = Depends(get_current_user),
):
    """Consulta el historial de movimientos de los últimos 3 días."""
    try:
        cfg = _cargar_banco_cfg(codigo)
        if not cfg:
            return JSONResponse(status_code=404, content={
                "status": "error", "message": f"Banco {codigo} no configurado"})

        tipo = cfg.get("tipo_api", "")
        if tipo != "bnc":
            return JSONResponse(status_code=400, content={
                "status": "error",
                "message": f"Historial no implementado para tipo '{tipo}'"})

        svc = _init_bnc_svc_from_cfg(cfg)
        res = svc.obtener_historial(
            client_id=cfg.get("client_id", ""),
            account_number=cfg.get("account_number", ""),
        )
        return {
            "status":       res.get("status", "error"),
            "banco":        cfg.get("nombre_banco", codigo),
            "codigo_banco": codigo,
            "cuenta":       cfg.get("account_number", ""),
            "total":        res.get("total", 0),
            "movimientos":  res.get("movimientos", []),
            "data_raw":     res.get("data"),
            "message":      res.get("message", ""),
        }
    except Exception as e:
        logger.error(f"consultar_historial_banco {codigo}: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/{codigo}/historial-fecha")
async def consultar_historial_fecha(
    codigo: str = Path(...),
    desde:  str = "",
    hasta:  str = "",
    user: models.User = Depends(get_current_user),
):
    """Consulta historial por rango de fechas (máximo 31 días). Formato: yyyy-MM-dd"""
    from datetime import date, timedelta
    if not desde:
        desde = (date.today() - timedelta(days=30)).isoformat()
    if not hasta:
        hasta = date.today().isoformat()
    try:
        cfg = _cargar_banco_cfg(codigo)
        if not cfg:
            return JSONResponse(status_code=404, content={
                "status": "error", "message": f"Banco {codigo} no configurado"})

        tipo = cfg.get("tipo_api", "")
        if tipo != "bnc":
            return JSONResponse(status_code=400, content={
                "status": "error",
                "message": f"Historial no implementado para tipo '{tipo}'"})

        svc = _init_bnc_svc_from_cfg(cfg)
        res = svc.obtener_historial_por_fecha(
            desde=desde, hasta=hasta,
            client_id=cfg.get("client_id", ""),
            account_number=cfg.get("account_number", ""),
        )
        return {
            "status":       res.get("status", "error"),
            "banco":        cfg.get("nombre_banco", codigo),
            "codigo_banco": codigo,
            "cuenta":       cfg.get("account_number", ""),
            "desde":        desde,
            "hasta":        hasta,
            "total":        res.get("total", 0),
            "movimientos":  res.get("movimientos", []),
            "data_raw":     res.get("data"),
            "message":      res.get("message", ""),
        }
    except Exception as e:
        logger.error(f"consultar_historial_fecha {codigo}: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/{codigo}/validar-pago-movil")
async def validar_pago_movil_banco(
    codigo:     str   = Path(...),
    referencia: str   = "",
    monto:      float = 0.0,
    telefono:   str   = "",
    cedula:     str   = "",
    fecha:      str   = "",
    user: models.User = Depends(get_current_user),
):
    """Valida un Pago Móvil recibido en el banco especificado."""
    try:
        cfg = _cargar_banco_cfg(codigo)
        if not cfg:
            return JSONResponse(status_code=404, content={
                "status": "error", "message": f"Banco {codigo} no configurado"})

        tipo = cfg.get("tipo_api", "")
        if tipo != "bnc":
            return JSONResponse(status_code=400, content={
                "status": "error",
                "message": f"Validación PM no implementada para tipo '{tipo}'"})

        svc = _init_bnc_svc_from_cfg(cfg)
        res = svc.validar_pago_bnc(
            referencia=referencia, monto=monto,
            tipo="p2p", telefono=telefono,
            cedula=cedula, fecha=fecha,
        )
        return {**res, "banco": cfg.get("nombre_banco", codigo), "codigo_banco": codigo}
    except Exception as e:
        logger.error(f"validar_pago_movil_banco {codigo}: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/disponibles")
async def bancos_disponibles(
    user: models.User = Depends(get_current_user),
):
    """Lista los bancos configurados y activos (para el KPI sidebar)."""
    try:
        conn, is_pg = _get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT codigo_banco, nombre_banco, tipo_api, account_number, "
            "notas FROM bancos_configuracion WHERE activo=1 ORDER BY nombre_banco"
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return {"status": "ok", "bancos": rows}
    except Exception as e:
        logger.error(f"bancos_disponibles: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

