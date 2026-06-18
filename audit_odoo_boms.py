import xmlrpc.client

odoo_url = 'http://192.168.1.193:8070'
odoo_db = 'carmal_odoo'
odoo_user = 'cvasquezdbelen@gmail.com'
odoo_pass = 'carmal2024'

common = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/common')
uid = common.authenticate(odoo_db, odoo_user, odoo_pass, {})
models = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/object')

# 1. Check BOMs
boms = models.execute_kw(odoo_db, uid, odoo_pass, 'mrp.bom', 'search_read', [[]], {
    'fields': ['id', 'code', 'product_tmpl_id', 'product_qty'],
    'limit': 10
})
print(f"Total BOMs: {len(boms)}")
for b in boms[:5]:
    print(f"  BOM id={b['id']} code={b['code']} product={b['product_tmpl_id']}")

# 2. Check BOM Lines
bom_ids = [b['id'] for b in boms]
if bom_ids:
    lines = models.execute_kw(odoo_db, uid, odoo_pass, 'mrp.bom.line', 'search_read',
        [[['bom_id', 'in', bom_ids[:3]]]], {'fields': ['bom_id', 'product_id', 'product_qty']})
    print(f"\nBOM Lines for first 3 BOMs: {len(lines)}")
    for l in lines[:5]:
        print(f"  BOM={l['bom_id'][1]} -> Component={l['product_id'][1]} qty={l['product_qty']}")

# 3. Check Odoo automated actions status
actions = models.execute_kw(odoo_db, uid, odoo_pass, 'base.automation', 'search_read', [[]], {
    'fields': ['id', 'name', 'active', 'model_id'],
    'limit': 20
})
print(f"\nAutomated Actions: {len(actions)}")
for a in actions:
    status = '✅ ACTIVE' if a['active'] else '❌ INACTIVE'
    print(f"  [{status}] {a['name']}")

# 4. Check Profit sync addon config
try:
    configs = models.execute_kw(odoo_db, uid, odoo_pass, 'res.config.settings', 'search_read', [[]], {
        'fields': [],
        'limit': 1
    })
    print(f"\nConfig Settings available: {len(configs)}")
except Exception as e:
    print(f"\nConfig Settings error: {e}")

# 5. Check if profit_sync module is installed
modules = models.execute_kw(odoo_db, uid, odoo_pass, 'ir.module.module', 'search_read',
    [[['state', '=', 'installed'], ['name', 'like', 'profit']]], {'fields': ['name', 'state']})
print(f"\nProfit modules installed: {modules}")
