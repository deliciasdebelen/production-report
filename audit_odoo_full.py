import xmlrpc.client, sys

odoo_url = 'http://192.168.1.193:8070'
odoo_db = 'carmal_odoo'
odoo_user = 'cvasquezdbelen@gmail.com'
odoo_pass = 'carmal2024'

common = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/common')
uid = common.authenticate(odoo_db, odoo_user, odoo_pass, {})
m = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/object')

# Full BOM summary
boms = m.execute_kw(odoo_db, uid, odoo_pass, 'mrp.bom', 'search_read', [[]], {'fields': ['id', 'code', 'product_tmpl_id']})
lines = m.execute_kw(odoo_db, uid, odoo_pass, 'mrp.bom.line', 'search_read', [[]], {'fields': ['bom_id', 'product_id', 'product_qty']})
counts = {}
for l in lines:
    bid = l['bom_id'][0]
    counts[bid] = counts.get(bid, 0) + 1
print(f"BOMs: {len(boms)} | Lines: {len(lines)}")
for b in boms:
    c = counts.get(b['id'], 0)
    print(f"  {b['code']:10} -> {b['product_tmpl_id'][1][:45]} [{c} lineas]")

# Profit sync config
print("\n--- Profit Sync Config ---")
try:
    fields = m.execute_kw(odoo_db, uid, odoo_pass, 'profit.sync.config', 'fields_get', [], {'attributes': ['string']})
    print(f"Model fields: {list(fields.keys())}")
    rec = m.execute_kw(odoo_db, uid, odoo_pass, 'profit.sync.config', 'search_read', [[]], {})
    for r in rec:
        print(f"  {r}")
except Exception as e:
    print(f"  ERROR: {e}")

# ir.config_parameter profit keys
print("\n--- ir.config_parameter profit ---")
params = m.execute_kw(odoo_db, uid, odoo_pass, 'ir.config_parameter', 'search_read',
    [[['key', 'like', 'profit']]], {'fields': ['key', 'value']})
for p in params:
    print(f"  {p['key']} = {p['value']}")

# Scheduled actions
print("\n--- Scheduled Actions ---")
crons = m.execute_kw(odoo_db, uid, odoo_pass, 'ir.cron', 'search_read',
    [[['name', 'like', 'profit']]], {'fields': ['name', 'active', 'interval_number', 'interval_type', 'nextcall']})
for c in crons:
    status = 'ON' if c['active'] else 'OFF'
    print(f"  [{status}] {c['name']} | cada {c['interval_number']} {c['interval_type']} | next: {c['nextcall']}")
