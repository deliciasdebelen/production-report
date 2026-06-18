import pyodbc
import xmlrpc.client

# Profit Plus DB
profit_server = '192.168.60.15'
profit_db = 'carmal_a'
profit_user = 'PROFIT'
profit_password = 'profit'
profit_cs = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={profit_server};DATABASE={profit_db};UID={profit_user};PWD={profit_password};Encrypt=no;TrustServerCertificate=yes"

# Odoo Connection
odoo_url = 'http://192.168.1.193:8070'
odoo_db = 'carmal_odoo'
odoo_user = 'cvasquezdbelen@gmail.com'
odoo_pass = 'carmal2024'

common = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/common')
uid = common.authenticate(odoo_db, odoo_user, odoo_pass, {})
if not uid:
    print("Odoo Auth failed.")
    exit(1)
models = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/object')

conn = pyodbc.connect(profit_cs)
cursor = conn.cursor()

# Get existing products from Odoo
odoo_pts = models.execute_kw(odoo_db, uid, odoo_pass, 'product.product', 'search_read', [[]], {'fields': ['id', 'default_code']})
existing_codes = {p['default_code'] for p in odoo_pts if p['default_code']}

cursor.execute("SELECT RTrim(co_art), RTrim(art_des), RTrim(co_lin) FROM saArticulo WHERE anulado=0")
articulos = cursor.fetchall()
print(f"Found {len(articulos)} articles in Profit.")

to_create = []
for f in articulos:
    code = f[0]
    name = f[1]
    line = f[2]
    
    if code not in existing_codes:
        to_create.append({
            'name': name,
            'default_code': code,
            'type': 'product',
            'x_profit_linea': line,
            'tracking': 'lot'
        })

print(f"New to create: {len(to_create)}")

# Create in chunks of 100
chunk_size = 100
success = 0
for i in range(0, len(to_create), chunk_size):
    chunk = to_create[i:i+chunk_size]
    try:
        new_ids = models.execute_kw(odoo_db, uid, odoo_pass, 'product.product', 'create', [chunk])
        success += len(new_ids)
        print(f"Created {success}/{len(to_create)}")
    except Exception as e:
        print(f"Error on chunk starting at {i}: {e}")

print(f"Done fast sync. Created {success}.")
