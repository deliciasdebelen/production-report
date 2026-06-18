"""
sync_products_odoo.py
Sincroniza artículos desde Profit Plus → Odoo.
Solo extrae las líneas: ME (Materiales de Empaque), MP (Materia Prima), PT (Producto Terminado), ST (Semi-terminado).
Fuente: carmal_a.saArticulo filtrado por saLineaArticulo.co_lin IN ('ME','MP','PT','ST')
"""
import pyodbc
import xmlrpc.client

# ─── Profit Plus ───────────────────────────────────────────────────────────────
PROFIT_CS = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.60.15;DATABASE=carmal_a;"
    "UID=PROFIT;PWD=profit;Encrypt=no;TrustServerCertificate=yes"
)

# ─── Odoo ──────────────────────────────────────────────────────────────────────
ODOO_URL  = 'http://192.168.1.193:8070'
ODOO_DB   = 'carmal_odoo'
ODOO_USER = 'cvasquezdbelen@gmail.com'
ODOO_PASS = 'carmal2024'

# Líneas habilitadas para sincronización
LINEAS_PERMITIDAS = ('ME', 'MP', 'PT', 'ST')

# Tracking por lote sólo para PT y ST (producto terminado y semi-terminado)
LINEAS_LOT_TRACKING = ('PT', 'ST')

# ─── Conexiones ───────────────────────────────────────────────────────────────
common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
uid    = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})
if not uid:
    print("ERROR: Autenticación en Odoo fallida.")
    exit(1)
models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

conn   = pyodbc.connect(PROFIT_CS)
cursor = conn.cursor()

# ─── Mapa actual de productos en Odoo: default_code → tmpl_id ─────────────────
print("Cargando catálogo de productos en Odoo...")
odoo_prods = models.execute_kw(ODOO_DB, uid, ODOO_PASS,
    'product.template', 'search_read', [[]],
    {'fields': ['id', 'default_code']})
tmpl_map = {p['default_code']: p['id'] for p in odoo_prods if p['default_code']}
print(f"   {len(tmpl_map)} productos cargados en Odoo.")

# ─── Extraer artículos de Profit filtrados por línea ─────────────────────────
print(f"\nExtrayendo artículos de Profit (líneas {LINEAS_PERMITIDAS})...")
cursor.execute("""
    SELECT
        RTRIM(LTRIM(a.co_art))  AS co_art,
        RTRIM(LTRIM(a.art_des)) AS art_des,
        RTRIM(LTRIM(a.co_lin))  AS co_lin
    FROM saArticulo a
    INNER JOIN saLineaArticulo l ON RTRIM(LTRIM(a.co_lin)) = RTRIM(LTRIM(l.co_lin))
    WHERE a.anulado = 0
      AND l.co_lin IN ('ME', 'MP', 'PT', 'ST')
    ORDER BY a.co_lin, a.co_art
""")
articulos = cursor.fetchall()
print(f"   {len(articulos)} artículos encontrados en Profit.")

# ─── Sincronización UPSERT ────────────────────────────────────────────────────
created = 0
updated = 0
failed  = 0

print("\nSincronizando...\n")
for art in articulos:
    code = art.co_art
    name = art.art_des
    linea = art.co_lin

    # PT y ST → con seguimiento de lote; ME y MP → sin lote
    tracking = 'lot' if linea in LINEAS_LOT_TRACKING else 'none'

    vals = {
        'name':          name,
        'default_code':  code,
        'type':          'product',       # Almacenable
        'x_profit_linea': linea,
        'tracking':      tracking,
    }

    try:
        if code in tmpl_map:
            models.execute_kw(ODOO_DB, uid, ODOO_PASS,
                'product.template', 'write', [[tmpl_map[code]], vals])
            updated += 1
        else:
            new_id = models.execute_kw(ODOO_DB, uid, ODOO_PASS,
                'product.template', 'create', [vals])
            tmpl_map[code] = new_id
            created += 1
    except Exception as e:
        print(f"  [ERROR] {code} ({linea}): {e}")
        failed += 1

# ─── Resumen ──────────────────────────────────────────────────────────────────
print("=" * 55)
print(f"  CREADOS     : {created}")
print(f"  ACTUALIZADOS: {updated}")
print(f"  ERRORES     : {failed}")
print(f"  TOTAL       : {created + updated + failed}")
print("=" * 55)
