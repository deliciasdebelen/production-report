import xmlrpc.client

odoo_url = 'http://192.168.1.193:8070'
odoo_db = 'carmal_odoo'
odoo_user = 'cvasquezdbelen@gmail.com'
odoo_pass = 'carmal2024'

common = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/common')
uid = common.authenticate(odoo_db, odoo_user, odoo_pass, {})
models = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/object')

# 1. Check total BOMs vs lines ratio
boms = models.execute_kw(odoo_db, uid, odoo_pass, 'mrp.bom', 'search_read', [[]], {
    'fields': ['id', 'code', 'product_tmpl_id', 'product_qty', 'type']
})
print(f"Total BOMs: {len(boms)}")

total_lines = models.execute_kw(odoo_db, uid, odoo_pass, 'mrp.bom.line', 'search_read', [[]], {
    'fields': ['id', 'bom_id', 'product_id', 'product_qty']
})
print(f"Total BOM Lines: {len(total_lines)}")

# Show all BOMs with their line count
bom_line_counts = {}
for l in total_lines:
    bom_id = l['bom_id'][0]
    bom_line_counts[bom_id] = bom_line_counts.get(bom_id, 0) + 1

print("\nBOM Summary:")
for b in boms:
    count = bom_line_counts.get(b['id'], 0)
    product_name = b['product_tmpl_id'][1] if b['product_tmpl_id'] else 'N/A'
    print(f"  {b['code']:10} | {product_name:40} | {count} componentes")

# 2. Check profit_sync config model
try:
    fields = models.execute_kw(odoo_db, uid, odoo_pass, 'profit.sync.config', 'fields_get', [], 
                               {'attributes': ['string', 'type']})
    print(f"\nprofit.sync.config fields: {list(fields.keys())}")
    
    records = models.execute_kw(odoo_db, uid, odoo_pass, 'profit.sync.config', 'search_read', [[]], {})
    print(f"Config records: {records}")
except Exception as e:
    print(f"\nprofit.sync.config not found: {e}")

# 3. Check ir.config_parameter for profit settings
params = models.execute_kw(odoo_db, uid, odoo_pass, 'ir.config_parameter', 'search_read',
    [[['key', 'like', 'profit']]], {'fields': ['key', 'value']})
print(f"\nProfit Parameters: {params}")
