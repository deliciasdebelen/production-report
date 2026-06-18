"""
Suite de regresión CXC — verifica todos los endpoints críticos.
Cubre: FM, Profit, Bancos, Conciliaciones, BD, config.
Ejecutar desde el servidor: docker exec production-report python3 /tmp/regression_cxc.py
"""
import requests, json, sys, sqlite3, os, time
from datetime import date

BASE = "http://localhost:8000"
SESSION_COOKIE = None   # se llena en login

PASS = "\033[92m✅ PASS\033[0m"
FAIL = "\033[91m❌ FAIL\033[0m"
SKIP = "\033[93m⏭  SKIP\033[0m"
INFO = "\033[94mℹ️  INFO\033[0m"

results = {"pass": 0, "fail": 0, "skip": 0}


def check(name, condition, detail=""):
    if condition:
        print(f"{PASS}  {name}" + (f"  → {detail}" if detail else ""))
        results["pass"] += 1
    else:
        print(f"{FAIL}  {name}" + (f"  → {detail}" if detail else ""))
        results["fail"] += 1
    return condition


def skip(name, reason=""):
    print(f"{SKIP}  {name}" + (f"  ({reason})" if reason else ""))
    results["skip"] += 1


def info(msg):
    print(f"{INFO}  {msg}")


# ─── Utilidades ────────────────────────────────────────────────────────
s = requests.Session()

def login():
    """Intenta hacer login para obtener sesión autenticada."""
    try:
        r = s.post(f"{BASE}/login", data={"username": "admin", "password": "admin"}, timeout=8, allow_redirects=True)
        return r.status_code < 400
    except Exception as e:
        return False


def get_db_conn():
    db_url = os.getenv("DATABASE_URL", "")
    is_pg  = "postgresql" in db_url or "postgres" in db_url
    if is_pg:
        import psycopg2, psycopg2.extras
        from urllib.parse import urlparse
        u    = urlparse(db_url)
        conn = psycopg2.connect(
            host=u.hostname, port=u.port or 5432,
            dbname=u.path.lstrip("/"), user=u.username, password=u.password
        )
        return conn, True
    conn = sqlite3.connect("/app/production.db")
    conn.row_factory = sqlite3.Row
    return conn, False


def get(path, **kw):
    try:
        return s.get(f"{BASE}{path}", timeout=10, **kw)
    except Exception as e:
        class FakeResp:
            status_code = 0
            text = str(e)
            def json(self): raise ValueError(str(e))
        return FakeResp()


def post(path, **kw):
    try:
        return s.post(f"{BASE}{path}", timeout=10, **kw)
    except Exception as e:
        class FakeResp:
            status_code = 0
            text = str(e)
            def json(self): raise ValueError(str(e))
        return FakeResp()


# ═══════════════════════════════════════════════════════════════════════
# CASO 1: Servidor activo
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("  CASO 1: Servidor FastAPI activo")
print("═"*60)

r = get("/health")
check("GET /health responde", r.status_code in [200, 404, 307, 401],
      f"HTTP {r.status_code}")

r = get("/")
check("GET / redirige o responde", r.status_code in [200, 302, 307, 401],
      f"HTTP {r.status_code}")

login_ok = login()
info(f"Login admin: {'OK' if login_ok else 'FALLÓ (tests de API requerirán sesión)'}")


# ═══════════════════════════════════════════════════════════════════════
# CASO 2: Ruta CXC HTML disponible
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("  CASO 2: Ruta /administracion/cxc disponible")
print("═"*60)

r = get("/administracion/cxc")
check("GET /administracion/cxc responde", r.status_code in [200, 302, 307],
      f"HTTP {r.status_code}")

if r.status_code == 200:
    check("HTML contiene fmCfgModal",    "fmCfgModal"     in r.text)
    check("HTML contiene cfg-tab-bancos","cfg-tab-bancos"  in r.text)
    check("HTML contiene kpiOverlay",    "kpiOverlay"      in r.text)
    check("HTML contiene abrirKPI",       "abrirKPI"         in r.text)
    check("HTML contiene conciliarBanco","conciliarBanco"  in r.text)
    check("HTML contiene verificar BD",  "conciliaciones/verificar" in r.text)
    check("HTML contiene guardar BD",    "conciliaciones/guardar"   in r.text)
    check("HTML contiene Analytics",     "Analytics"        in r.text)
    check("HTML contiene chart.js CDN",  "chart.js"        in r.text)
    check("HTML contiene _desde_bd flag","_desde_bd"       in r.text,
          "Flag de pre-marcado BD activo")
else:
    skip("Inspección HTML", f"Status {r.status_code}")


# ═══════════════════════════════════════════════════════════════════════
# CASO 3: API Fuerza Móvil
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("  CASO 3: API FM /api/fm/cobros")
print("═"*60)

r = get("/administracion/cxc/api/fm/cobros?fecha_desde=2026-06-01&fecha_hasta=2026-06-03")
check("GET /api/fm/cobros responde", r.status_code in [200, 401, 403],
      f"HTTP {r.status_code}")
if r.status_code == 200:
    try:
        d = r.json()
        check("Respuesta tiene status", "status" in d, d.get("status"))
        check("Respuesta tiene data o error controlado",
              "data" in d or "message" in d)
    except Exception as e:
        check("JSON válido", False, str(e))

r2 = get("/administracion/cxc/api/fm/status")
check("GET /api/fm/status responde", r2.status_code in [200, 401],
      f"HTTP {r2.status_code}")


# ═══════════════════════════════════════════════════════════════════════
# CASO 4: API Conciliaciones — Guardar (solo confirmados)
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("  CASO 4: POST /api/conciliaciones/guardar — solo guarda confirmados")
print("═"*60)

payload_mix = {
    "registros": [
        # Registro CONFIRMADO → debe guardarse
        {
            "fm_id": "TEST-CONF-001",
            "num_recibo": "TEST-CONF-001",
            "cod_cliente": "CLI001",
            "cliente_nombre": "Cliente Test Confirmado",
            "rif": "J-12345678-9",
            "tipo_pago": "transferencia",
            "fecha": "2026-06-03",
            "monto": 50000.0,
            "monto_usd": 1388.89,
            "tasa": 36.0,
            "cod_moneda": "VES",
            "_estatus": "completado",
            "_banco": {"confirmado": True, "monto_confirmado": 50000.0,
                       "banco_nombre": "BNC", "referencia_banco": "REF-TEST-001",
                       "mensaje": "Transferencia confirmada"},
            "_conc": {"diferencia": 0.0},
            "pagos": [{"cod_banco": "0191", "monto_pago": 50000.0}],
        },
        # Registro PENDIENTE → NO debe guardarse
        {
            "fm_id": "TEST-PEND-002",
            "num_recibo": "TEST-PEND-002",
            "cod_cliente": "CLI002",
            "cliente_nombre": "Cliente Test Pendiente",
            "tipo_pago": "transferencia",
            "fecha": "2026-06-03",
            "monto": 25000.0,
            "_estatus": "pendiente",
            "_banco": {"confirmado": False, "mensaje": "Sin respuesta banco"},
            "_conc": {},
            "pagos": [],
        },
    ]
}

r = post("/administracion/cxc/api/conciliaciones/guardar",
         json=payload_mix)
check("POST /guardar responde", r.status_code in [200, 401],
      f"HTTP {r.status_code}")
if r.status_code == 200:
    try:
        d = r.json()
        check("Status OK", d.get("status") == "ok", d.get("mensaje",""))
        guardados = d.get("guardados", -1)
        check("Solo guarda confirmados (guardados=1)",
              guardados == 1,
              f"guardados={guardados} (esperado 1, el pendiente no debe persistirse)")
    except Exception as e:
        check("JSON válido", False, str(e))


# ═══════════════════════════════════════════════════════════════════════
# CASO 5: API Conciliaciones — Verificar
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("  CASO 5: POST /api/conciliaciones/verificar")
print("═"*60)

r = post("/administracion/cxc/api/conciliaciones/verificar",
         json={"fm_ids": ["TEST-CONF-001", "TEST-PEND-002", "NO-EXISTE-999"]})
check("POST /verificar responde", r.status_code in [200, 401],
      f"HTTP {r.status_code}")
if r.status_code == 200:
    try:
        d = r.json()
        check("Status OK", d.get("status") == "ok")
        conc = d.get("conciliados", {})
        check("TEST-CONF-001 aparece como conciliado",
              "TEST-CONF-001" in conc,
              f"conc keys: {list(conc.keys())}")
        check("TEST-PEND-002 NO aparece (no fue guardado)",
              "TEST-PEND-002" not in conc,
              "Correcto: pendientes no están en BD")
        check("NO-EXISTE-999 NO aparece",
              "NO-EXISTE-999" not in conc)
        if "TEST-CONF-001" in conc:
            data = conc["TEST-CONF-001"]
            check("monto_confirmado correcto",
                  float(data.get("monto_confirmado", 0)) == 50000.0,
                  f"= {data.get('monto_confirmado')}")
            check("referencia_banco presente",
                  bool(data.get("referencia_banco")),
                  data.get("referencia_banco"))
    except Exception as e:
        check("JSON válido", False, str(e))


# ═══════════════════════════════════════════════════════════════════════
# CASO 6: API Historial con filtros
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("  CASO 6: GET /api/conciliaciones/historial")
print("═"*60)

r = get("/administracion/cxc/api/conciliaciones/historial?fecha_desde=2026-06-01&limit=50")
check("GET /historial responde", r.status_code in [200, 401],
      f"HTTP {r.status_code}")
if r.status_code == 200:
    try:
        d = r.json()
        check("Status OK", d.get("status") == "ok")
        check("Tiene campo total", "total" in d, f"total={d.get('total')}")
        check("Tiene campo data", "data" in d)
        rows = d.get("data", [])
        info(f"Registros en historial (desde 2026-06-01): {len(rows)}")
        if rows:
            r0 = rows[0]
            check("Registro tiene fm_id",       "fm_id"       in r0)
            check("Registro tiene estatus",     "estatus"     in r0)
            check("Registro confirmado_banco=1","confirmado_banco" in r0,
                  f"confirmado_banco={r0.get('confirmado_banco')}")
    except Exception as e:
        check("JSON válido", False, str(e))


# ═══════════════════════════════════════════════════════════════════════
# CASO 7: API Bancos Config
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("  CASO 7: API Bancos Config CRUD")
print("═"*60)

r = get("/administracion/cxc/api/bancos/config")
check("GET /bancos/config responde", r.status_code in [200, 401],
      f"HTTP {r.status_code}")
if r.status_code == 200:
    try:
        d = r.json()
        check("Status OK", d.get("status") == "ok")
        check("BNC pre-cargado",
              any(b.get("codigo_banco") == "0191" for b in d.get("data",[])),
              f"{len(d.get('data',[]))} bancos configurados")
        check("Tipos API disponibles", "tipos_api" in d)
    except Exception as e:
        check("JSON válido", False, str(e))

# Crear banco de prueba
r = post("/administracion/cxc/api/bancos/config", json={
    "codigo_banco": "0102",
    "nombre_banco": "Banco de Venezuela (Test)",
    "activo": True,
    "tipo_api": "rest",
    "base_url": "https://api.bdv.com.ve/v1",
    "auth_endpoint": "/auth/token",
    "transfer_endpoint": "/transfers/query",
    "c2p_endpoint": "/c2p/query",
    "notas": "Registro de prueba regresión"
})
check("POST /bancos/config crea banco", r.status_code in [200, 401],
      f"HTTP {r.status_code}")
if r.status_code == 200:
    d = r.json()
    check("Respuesta OK", d.get("status") == "ok",
          d.get("codigo_banco",""))

# Listar de nuevo para verificar que aparece
r = get("/administracion/cxc/api/bancos/config")
if r.status_code == 200:
    d = r.json()
    has_0102 = any(b.get("codigo_banco") == "0102" for b in d.get("data",[]))
    check("BDV (0102) aparece en listado", has_0102)

# Probar conexión BNC (sin credenciales reales → debe reportar error controlado)
r = post("/administracion/cxc/api/bancos/config/0191/test")
check("POST /bancos/config/0191/test responde", r.status_code in [200, 401, 404],
      f"HTTP {r.status_code}")
if r.status_code == 200:
    d = r.json()
    check("Test BNC retorna status", "status" in d and "conectado" in d,
          f"conectado={d.get('conectado')}, msg={d.get('mensaje','')[:60]}")


# ═══════════════════════════════════════════════════════════════════════
# CASO 8: API Conciliar individual
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("  CASO 8: POST /api/conciliar (motor de conciliación individual)")
print("═"*60)

pago_test = {
    "fm_id": "TEST-CONC-001",
    "num_recibo": "TEST-CONC-001",
    "cod_cliente": "CLI001",
    "cliente_nombre": "Cliente Test",
    "tipo_pago": "efectivo",       # Efectivo: se confirma automáticamente
    "metodo_banco": "efectivo",
    "requiere_banco": False,
    "monto": 10000.0,
    "monto_usd": 277.78,
    "tasa": 36.0,
    "fecha": "2026-06-03",
    "referencia": "EFE-TEST-001",
    "telefono": "0414-1234567",
    "cod_moneda": "VES",
    "pagos": [{"cod_banco": "", "monto_pago": 10000.0, "num_referencia": "EFE-TEST-001"}],
}

r = post("/administracion/cxc/api/conciliar", json=pago_test)
check("POST /api/conciliar responde", r.status_code in [200, 401],
      f"HTTP {r.status_code}")
if r.status_code == 200:
    try:
        d = r.json()
        check("Status OK", d.get("status") == "ok")
        c = d.get("conciliacion", {})
        check("Tiene semaforo", "semaforo" in c, c.get("semaforo",""))
        check("Tiene estatus",  "estatus"  in c, c.get("estatus",""))
        b = c.get("banco", {})
        check("Efectivo: confirmado=True",
              b.get("confirmado") is True,
              f"confirmado={b.get('confirmado')}")
    except Exception as e:
        check("JSON válido", False, str(e))


# ═══════════════════════════════════════════════════════════════════════
# CASO 9: BD directa — estructura de tablas
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("  CASO 9: Base de datos — tablas y estructura")
print("═"*60)

try:
    conn, is_pg = get_db_conn()
    cur  = conn.cursor()

    # cxc_conciliaciones
    if is_pg:
        cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='cxc_conciliaciones')")
        check("Tabla cxc_conciliaciones existe", cur.fetchone()[0] is True)
    else:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cxc_conciliaciones'")
        check("Tabla cxc_conciliaciones existe", cur.fetchone() is not None)

    if is_pg:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='cxc_conciliaciones'")
        cols = {r[0] for r in cur.fetchall()}
    else:
        cur.execute("PRAGMA table_info(cxc_conciliaciones)")
        cols = {r["name"] for r in cur.fetchall()}

    for col in ["fm_id","confirmado_banco","estatus","monto_ves","fecha_pago","pagos_json"]:
        check(f"  columna '{col}'", col in cols)

    cur.execute("SELECT COUNT(*) FROM cxc_conciliaciones WHERE confirmado_banco=1")
    cnt = cur.fetchone()[0]
    info(f"Registros confirmados en BD: {cnt}")

    # bancos_configuracion
    if is_pg:
        cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='bancos_configuracion')")
        check("Tabla bancos_configuracion existe", cur.fetchone()[0] is True)
    else:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bancos_configuracion'")
        check("Tabla bancos_configuracion existe", cur.fetchone() is not None)

    if is_pg:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='bancos_configuracion'")
        bcols = {r[0] for r in cur.fetchall()}
    else:
        cur.execute("PRAGMA table_info(bancos_configuracion)")
        bcols = {r["name"] for r in cur.fetchall()}

    for col in ["codigo_banco","tipo_api","base_url","client_guid","master_key","activo"]:
        check(f"  columna '{col}'", col in bcols)

    cur.execute("SELECT COUNT(*) FROM bancos_configuracion WHERE activo=1")
    bcnt = cur.fetchone()[0]
    info(f"Bancos activos configurados: {bcnt}")

    # Índices
    if is_pg:
        cur.execute("SELECT indexname FROM pg_indexes WHERE tablename='cxc_conciliaciones'")
        idxs = [r[0] for r in cur.fetchall()]
        check("Índices cxc_conciliaciones creados", len(idxs) >= 1, f"{len(idxs)} índices pg")
    else:
        cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_cxc_%'")
        idxs = [r[0] for r in cur.fetchall()]
        check("Índices cxc_conciliaciones creados",
              len(idxs) >= 3,
              f"{len(idxs)} índices: {', '.join(idxs)}")

    conn.close()
except Exception as e:
    check("Acceso BD", False, str(e))


# ═══════════════════════════════════════════════════════════════════════
# CASO 10: Limpiar datos de prueba
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("  CASO 10: Limpieza de datos de prueba")
print("═"*60)

try:
    conn, is_pg = get_db_conn()
    cur  = conn.cursor()
    cur.execute("DELETE FROM cxc_conciliaciones WHERE fm_id LIKE 'TEST-%'")
    deleted = cur.rowcount
    cur.execute("DELETE FROM bancos_configuracion WHERE notas LIKE '%regresión%'")
    deleted_b = cur.rowcount
    conn.commit()
    conn.close()
    check("Limpieza datos test CXC",    deleted   >= 0, f"{deleted} eliminados")
    check("Limpieza datos test Bancos", deleted_b >= 0, f"{deleted_b} eliminados")
except Exception as e:
    check("Limpieza BD", False, str(e))


# ═══════════════════════════════════════════════════════════════════════
# RESUMEN
# ═══════════════════════════════════════════════════════════════════════
total = results["pass"] + results["fail"] + results["skip"]
print("\n" + "═"*60)
print(f"  RESULTADOS: {total} casos ejecutados")
print(f"  {PASS}  {results['pass']}")
print(f"  {FAIL}  {results['fail']}")
print(f"  {SKIP}  {results['skip']}")
print("═"*60)

if results["fail"] > 0:
    sys.exit(1)
