import xmlrpc.client

url = 'http://192.168.1.193:8070'
db = 'carmal_odoo'
user = 'cvasquezdbelen@gmail.com'
pwd = 'carmal2024'

c = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = c.authenticate(db, user, pwd, {})
m = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

mos=m.execute_kw(db,uid,pwd,'mrp.production','search_read',[[]], {'fields':['id','name','state'],'order':'id desc','limit':3})
for mo in mos:
    print(f"MO: {mo['name']}, ID: {mo['id']}")
    msgs=m.execute_kw(db,uid,pwd,'mail.message','search_read',[[['res_id','=',mo['id']],['model','=','mrp.production']]],{'fields':['body'],'order':'id desc','limit':5})
    for msg in msgs:
        print(f"  -> {msg['body'][:200]}")
