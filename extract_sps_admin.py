import pyodbc

conn_str = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;DATABASE=MasterProfitPro;UID=PROFIT;PWD=profit;Encrypt=yes;TrustServerCertificate=yes;'
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

sps = [
    'pMigradorAdmin', 'pInsertarMapaAdmi', 'pActualizarMapaAdmi', 
    'pEliminarMapaAdmi', 'pInsertarUsuarioAdmi', 'pActualizarUsuarioAdmi', 'pEliminarUsuarioAdmi'
]

with open('master_admin_sps_fixed.md', 'w', encoding='utf-8') as f:
    f.write('# Admin SPs\n')
    for sp in sps:
        f.write(f'\n## {sp}\n\n')
print('Done dumping')
