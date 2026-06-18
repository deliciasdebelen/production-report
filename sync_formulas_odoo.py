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

# Get products map from Odoo: internal reference -> product_id
odoo_pts = models.execute_kw(odoo_db, uid, odoo_pass, 'product.product', 'search_read', [[]], {'fields': ['id', 'default_code']})
product_map = {p['default_code']: p['id'] for p in odoo_pts if p['default_code']}

cursor.execute("SELECT co_artc, descrip, co_art, co_uni FROM saArtCompuesto")
formulas = cursor.fetchall()

success = 0
failed = 0

for f in formulas:
    bom_code = f.co_artc.strip()
    pt_code = f.co_art.strip()
    
    if pt_code not in product_map:
        # print(f"BOM {bom_code}: PT {pt_code} not found in Odoo.")
        failed += 1
        continue
        
    pt_id = product_map[pt_code]
    
    try:
        # Get product_tmpl_id
        pt_data = models.execute_kw(odoo_db, uid, odoo_pass, 'product.product', 'read', [[pt_id]], {'fields': ['product_tmpl_id']})
        tmpl_id = pt_data[0]['product_tmpl_id'][0]
        
        # Create BOM Header
        bom_id = models.execute_kw(odoo_db, uid, odoo_pass, 'mrp.bom', 'create', [{
            'product_tmpl_id': tmpl_id,
            'product_id': pt_id,
            'code': bom_code,
            'type': 'normal'
        }])
        
        # Get components
        cursor.execute("SELECT co_art, total_art FROM saArtCompuestoReng WHERE co_artc=?", f.co_artc)
        lines = cursor.fetchall()
        
        for l in lines:
            comp_code = l.co_art.strip()
            comp_qty = float(l.total_art)
            
            if comp_code not in product_map:
                print(f"  Line for BOM {bom_code}: Component {comp_code} not found in Odoo. Skipping line.")
                continue
                
            comp_id = product_map[comp_code]
            
            models.execute_kw(odoo_db, uid, odoo_pass, 'mrp.bom.line', 'create', [{
                'bom_id': bom_id,
                'product_id': comp_id,
                'product_qty': comp_qty
            }])
            
        print(f"Created BOM {bom_code} for {pt_code} with {len(lines)} lines.")
        success += 1
    except Exception as e:
        print(f"Error creating BOM {bom_code} for {pt_code}: {e}")
        failed += 1

print(f"Done. Successfully created {success} BOMs. Failed/Skipped: {failed}")
