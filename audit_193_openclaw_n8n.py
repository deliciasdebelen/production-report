import paramiko, requests, json

HOST_193 = "192.168.1.193"
USER     = "administrador"
PASS     = "GRW7czL3*"

def ssh(cmd, timeout=30):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST_193, 22, USER, PASS, timeout=10)
    _, out, err = c.exec_command(cmd, timeout=timeout)
    r = out.read().decode("utf-8", errors="replace").strip()
    e = err.read().decode("utf-8", errors="replace").strip()
    c.close()
    return r or e

SUDO = f'echo "{PASS}" | sudo -S'

print("=" * 60)
print("SERVIDOR 192.168.1.193 - OpenClaw + n8n + procesos activos")
print("=" * 60)

# 1. Todos los contenedores
print("\n[1] TODOS los contenedores en .193:")
print(ssh(f'{SUDO} docker ps -a --format "{{{{.Names}}}}\\t{{{{.Image}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}" 2>&1'))

# 2. Conectividad a 205 (carmal_a = SQL Server)
print("\n[2] Conectividad desde .193 hacia 192.168.1.205:")
print(ssh(f'nc -z -w 3 192.168.1.205 1433 2>&1 && echo "MSSQL 1433: OPEN" || echo "MSSQL 1433: CLOSED"'))
print(ssh(f'ping -c 2 192.168.1.205 2>&1 | tail -2'))

# 3. n8n workflows activos (DB SQLite dentro del contenedor)
print("\n[3] n8n - Workflows ACTIVOS:")
print(ssh(f'{SUDO} docker exec $(docker ps -q --filter name=n8n) sqlite3 /home/node/.n8n/database.sqlite "SELECT id, name, active FROM workflow_entity ORDER BY active DESC;" 2>&1'))

# 4. n8n - credenciales de SQL Server / MSSQL
print("\n[4] n8n - Credenciales con SQL Server / carmal:")
print(ssh(f'{SUDO} docker exec $(docker ps -q --filter name=n8n) sqlite3 /home/node/.n8n/database.sqlite "SELECT id, name, type FROM credentials_entity;" 2>&1'))

# 5. n8n - executions recientes (ultimas 10)
print("\n[5] n8n - Ejecuciones recientes (ultimas 10):")
print(ssh(f'{SUDO} docker exec $(docker ps -q --filter name=n8n) sqlite3 /home/node/.n8n/database.sqlite "SELECT id, workflowId, status, startedAt, stoppedAt FROM execution_entity ORDER BY startedAt DESC LIMIT 10;" 2>&1'))

# 6. n8n logs recientes
print("\n[6] n8n - Logs recientes (50 lineas):")
print(ssh(f'{SUDO} docker logs $(docker ps -q --filter name=n8n) --tail 50 2>&1'))

# 7. OpenClaw/OpenWebUI - logs recientes
print("\n[7] OpenClaw/OpenWebUI - logs recientes:")
print(ssh(f'{SUDO} docker logs $(docker ps -q --filter name=open 2>/dev/null | head -1) --tail 30 2>&1 || echo "Intentando por nombre..."'))
print(ssh(f'{SUDO} docker ps -q --filter name=open 2>&1'))
print(ssh(f'{SUDO} docker logs open-webui --tail 30 2>&1 || docker logs openwebui --tail 30 2>&1 || echo "Container openwebui no encontrado con ese nombre"'))

# 8. Variables de entorno de n8n (buscar conexiones a BD)
print("\n[8] n8n - Variables de entorno (BD, SQL, carmal):")
print(ssh(f'{SUDO} docker exec $(docker ps -q --filter name=n8n) env 2>&1 | grep -iE "db|sql|host|mssql|carmal|profit|odoo|205"'))

# 9. n8n - Nodos activos que usan SQL Server en workflows
print("\n[9] n8n - Workflows con nodo MSSQL/SQL Server:")
print(ssh(f'{SUDO} docker exec $(docker ps -q --filter name=n8n) sqlite3 /home/node/.n8n/database.sqlite "SELECT id, name, active, nodes FROM workflow_entity WHERE nodes LIKE \'%mssql%\' OR nodes LIKE \'%sqlserver%\' OR nodes LIKE \'%carmal%\';" 2>&1'))

# 10. Ollama en .193
print("\n[10] Ollama en .193 - modelos cargados:")
print(ssh(f'{SUDO} docker exec $(docker ps -q --filter name=ollama) ollama list 2>&1 || echo "ollama no encontrado"'))

# 11. Cron jobs en .193
print("\n[11] Cron jobs activos en .193:")
print(ssh(f'crontab -l 2>&1'))
print(ssh(f'{SUDO} cat /etc/cron.d/* 2>&1 | head -30'))
