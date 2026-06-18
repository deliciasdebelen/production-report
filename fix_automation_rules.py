import xmlrpc.client

odoo_url = 'http://192.168.1.193:8070'
odoo_db = 'carmal_odoo'
odoo_user = 'cvasquezdbelen@gmail.com'
odoo_pass = 'carmal2024'

common = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/common')
uid = common.authenticate(odoo_db, odoo_user, odoo_pass, {})

if not uid:
    print("Failed to auth to Odoo")
    exit(1)

models = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/object')

# 1. Search for Traslado rule and deactivate it.
rules = models.execute_kw(odoo_db, uid, odoo_pass, 'base.automation', 'search_read', 
    [[['name', 'ilike', 'traslado']]], {'fields': ['id', 'name', 'active']})

for rule in rules:
    print(f"Found rule: {rule['name']} (ID: {rule['id']}, Active: {rule['active']})")
    if rule['active']:
        models.execute_kw(odoo_db, uid, odoo_pass, 'base.automation', 'write', [[rule['id']], {'active': False}])
        print(f" -> Deactivated rule {rule['name']}")

# 2. Check for Ajuste Inventario rule
rules_ajuste = models.execute_kw(odoo_db, uid, odoo_pass, 'base.automation', 'search_read', 
    [[['name', 'ilike', 'ajuste']]], {'fields': ['id', 'name', 'active']})

for rule in rules_ajuste:
    print(f"Found rule: {rule['name']} (ID: {rule['id']}, Active: {rule['active']})")
    if not rule['active']:
        models.execute_kw(odoo_db, uid, odoo_pass, 'base.automation', 'write', [[rule['id']], {'active': True}])
        print(f" -> Activated rule {rule['name']}")

print("Automation Rules adjusted properly.")
