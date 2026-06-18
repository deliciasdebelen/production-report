import paramiko, json, requests

HOST_79 = "192.168.1.79"
USER    = "administrador"
PASS    = "GRW7czL3*"

def ssh(cmd, timeout=30):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST_79, 22, USER, PASS, timeout=10)
    _, out, err = c.exec_command(cmd, timeout=timeout)
    r = out.read().decode("utf-8", errors="replace").strip()
    c.close()
    return r

SUDO = f'echo "{PASS}" | sudo -S'

print("=" * 60)
print("AUDITORIA DETALLADA: n8n + Ollama + carmal_a (SQL Server .205)")
print("=" * 60)

# 1. Workflows activos en n8n (API)
print("\n[1] n8n Workflows via API:")
try:
    r = requests.get("http://192.168.1.79:5678/api/v1/workflows?active=true",
                     headers={"X-N8N-API-KEY": "n8n_api_key_placeholder"},
                     timeout=5)
    print(f"Status: {r.status_code}")
    if r.ok:
        data = r.json()
        for wf in data.get("data", []):
            print(f"  - [{wf['id']}] {wf['name']} | active={wf['active']}")
    else:
        print(r.text[:300])
except Exception as e:
    print(f"API error: {e}")

# 2. n8n database (SQLite dentro del container)
print("\n[2] Workflows en DB de n8n (SQLite):")
print(ssh(f'{SUDO} docker exec ia_musculo sqlite3 /home/node/.n8n/database.sqlite "SELECT id, name, active FROM workflow_entity WHERE active=1 ORDER BY id;" 2>&1 | head -30'))

# 3. Credenciales n8n (buscar referencias a SQL Server / carmal)
print("\n[3] Credenciales n8n con SQL Server:")
print(ssh(f'{SUDO} docker exec ia_musculo sqlite3 /home/node/.n8n/database.sqlite "SELECT id, name, type, data FROM credentials_entity WHERE type LIKE \'%sql%\' OR type LIKE \'%mssql%\' OR name LIKE \'%carmal%\' OR name LIKE \'%profit%\';" 2>&1 | head -30'))

# 4. Modelos cargados en Ollama (ia_cerebro)
print("\n[4] Modelos en Ollama (ia_cerebro):")
print(ssh(f'{SUDO} docker exec ia_cerebro ollama list 2>&1'))

# 5. Logs recientes de n8n
print("\n[5] Últimos logs de n8n (ia_musculo - 50 lineas):")
print(ssh(f'{SUDO} docker logs ia_musculo --tail 40 2>&1'))

# 6. Logs recientes de Ollama
print("\n[6] Últimos logs de Ollama (ia_cerebro - 20 lineas):")
print(ssh(f'{SUDO} docker logs ia_cerebro --tail 20 2>&1'))

# 7. Buscar referencias a carmal_a en archivos n8n
print("\n[7] Config n8n env vars:")
print(ssh(f'{SUDO} docker exec ia_musculo env 2>&1 | grep -iE "db|sql|host|carmal|profit|205"'))

# 8. Belen scheduler (automatizacion interna)
print("\n[8] belen_scheduler.py - contenido:")
print(ssh("head -60 /home/administrador/apps/production-report/belen_scheduler.py 2>&1"))

# 9. sync_profit_replica.py
print("\n[9] sync_profit_replica.py - head:")
print(ssh("head -50 /home/administrador/apps/production-report/sync_profit_replica.py 2>&1"))
