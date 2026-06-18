import paramiko

HOST_193 = "192.168.1.193"
USER     = "administrador"
PASS     = "GRW7czL3*"

def ssh(cmd, timeout=30):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST_193, 22, USER, PASS, timeout=10)
    _, out, _ = c.exec_command(cmd, timeout=timeout)
    r = out.read().decode("utf-8", errors="replace").strip()
    c.close()
    return r

SUDO = f'echo "{PASS}" | sudo -S'

print("=" * 60)
print("n8n DATABASE SQLITE - WORKFLOWS Y CREDENCIALES")
print("=" * 60)

# Copiar SQLite fuera del contenedor para leerla
print("\n[1] Workflows en n8n DB:")
print(ssh(f'''{SUDO} docker exec n8n sqlite3 /home/node/.n8n/database.sqlite "SELECT id, name, active, updatedAt FROM workflow_entity ORDER BY active DESC, updatedAt DESC;" 2>&1'''))

print("\n[2] Credenciales registradas:")
print(ssh(f'''{SUDO} docker exec n8n sqlite3 /home/node/.n8n/database.sqlite "SELECT id, name, type, createdAt, updatedAt FROM credentials_entity;" 2>&1'''))

print("\n[3] Executions recientes (ultimas 20):")
print(ssh(f'''{SUDO} docker exec n8n sqlite3 /home/node/.n8n/database.sqlite "SELECT id, workflowId, status, startedAt, stoppedAt FROM execution_entity ORDER BY startedAt DESC LIMIT 20;" 2>&1'''))

print("\n[4] Workflows con contenido (nodos):")
print(ssh(f'''{SUDO} docker exec n8n sqlite3 /home/node/.n8n/database.sqlite "SELECT id, name, active, substr(nodes, 1, 200) as nodes_preview FROM workflow_entity;" 2>&1'''))

print("\n[5] openclaw - ubicacion y version:")
print(ssh("cat /home/administrador/.nvm/versions/node/v22.22.0/lib/node_modules/openclaw/package.json 2>&1 | grep -E 'name|version|description' | head -5"))

print("\n[6] openclaw - extension plugins instalados:")
print(ssh("ls -la /home/administrador/.nvm/versions/node/v22.22.0/lib/node_modules/openclaw/extensions/ 2>&1"))

print("\n[7] openclaw - procesos activos:")
print(ssh("ps aux | grep -i openclaw | grep -v grep"))
print(ssh("ps aux | grep -i n8n | grep -v grep"))

print("\n[8] Conexiones activas a SQL Server en .193:")
print(ssh("ss -tnp | grep 1433"))
print(ssh("ss -tnp | grep ':1433'"))

print("\n[9] Proceso python con conexion a 192.168.60.15:1433 (Profit DB):")
print(ssh("ps aux | grep -E 'python|sync|profit|carmal' | grep -v grep | head -10"))

print("\n[10] Open-WebUI - causa del crash:")
print(ssh(f'{SUDO} docker logs open-webui --tail 10 2>&1'))

print("\n[11] open-webui ENV vars (para ver DB y conexiones):")
print(ssh(f'{SUDO} docker inspect open-webui 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin)[0]; env=d.get(\'Config\',{{}}).get(\'Env\',[]); [print(e) for e in env if any(k in e.upper() for k in [\'DB\',\'SQL\',\'CARMAL\',\'OPENAI\',\'OLLAMA\',\'MODEL\',\'URL\',\'PORT\',\'205\',\'193\'])]" 2>&1'))
