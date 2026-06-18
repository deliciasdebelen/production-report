import paramiko

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

N8N_CTR = "$(docker ps -q --filter name=n8n | head -1)"

print("=" * 60)
print("n8n - WORKFLOWS Y CONEXIONES CARMAL_A (SQL Server .205)")
print("=" * 60)

# n8n usa PostgreSQL o su propia DB - encontrar cual
print("\n[A] n8n - Tipo de base de datos interna:")
print(ssh(f'{SUDO} docker exec {N8N_CTR} env 2>&1 | grep -iE "DB_|DATABASE|POSTGRES|SQLITE|MYSQL"'))

# Encontrar el nombre exacto del contenedor n8n
print("\n[B] Nombre exacto del contenedor n8n:")
print(ssh(f'docker ps --filter name=n8n --format "{{{{.Names}}}}\\t{{{{.ID}}}}"'))

# n8n con postgres - listar workflows
print("\n[C] n8n - Listar workflows via psql (si usa postgres):")
print(ssh(f'{SUDO} docker exec {N8N_CTR} node -e "const{{Client}}=require(\'pg\'); const c=new Client(); c.connect().then(()=>c.query(\'SELECT id,name,active FROM workflow_entity ORDER BY active DESC\')).then(r=>console.log(JSON.stringify(r.rows,null,2))).catch(e=>console.log(\'pg err:\',e.message))" 2>&1 | head -40'))

# n8n API REST directa
print("\n[D] n8n API - Workflows (sin auth):")
import urllib.request
try:
    req = urllib.request.urlopen("http://192.168.1.193:5678/api/v1/workflows", timeout=5)
    print(req.read().decode()[:1000])
except Exception as e:
    print(f"Error sin auth: {e}")

# n8n internals via node
print("\n[E] n8n - Workflows via node interno:")
node_script = """
const path = '/home/node/.n8n';
const fs = require('fs');
try {
  const files = fs.readdirSync(path);
  console.log('Files in .n8n:', files.join(', '));
} catch(e) { console.log('Error:', e.message); }
"""
print(ssh(f'{SUDO} docker exec {N8N_CTR} node -e "{node_script}" 2>&1'))

# Buscar archivo de workflows exportados
print("\n[F] Buscar exports/backups de workflows n8n:")
print(ssh(f'find /home/administrador -name "*.json" -newer /home/administrador/.bashrc 2>/dev/null | xargs grep -l "workflow\\|n8n" 2>/dev/null | head -10'))
print(ssh(f'ls -la /home/administrador/apps/ 2>&1'))

# Verificar si n8n usa postgres propio
print("\n[G] Contenedores con postgres en .193:")
print(ssh(f'{SUDO} docker ps -a --format "{{{{.Names}}}}\\t{{{{.Image}}}}" 2>&1 | grep -i "postgres\\|pg\\|db"'))

# n8n filesystem - buscar credenciales MSSQL
print("\n[H] n8n - Buscar archivos de credenciales:")
print(ssh(f'{SUDO} docker exec {N8N_CTR} sh -c "find /home/node/.n8n -type f 2>/dev/null | head -20"'))
print(ssh(f'{SUDO} docker exec {N8N_CTR} sh -c "ls -la /home/node/.n8n/ 2>&1"'))

# Open WebUI - estado real
print("\n[I] Open WebUI - estado del contenedor:")
print(ssh(f'{SUDO} docker ps -a --filter name=open 2>&1'))
print(ssh(f'{SUDO} docker inspect $(docker ps -aq --filter name=open | head -1) 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0][\'Name\'], d[0][\'State\'][\'Status\'], d[0][\'State\'][\'Error\'][:200] if d[0][\'State\'][\'Error\'] else \'OK\')" 2>&1'))

# Tráfico SQL Server hacia .205 desde .193
print("\n[J] Conexiones activas hacia 192.168.1.205:1433 desde .193:")
print(ssh(f'ss -tnp | grep 1433 || netstat -tnp 2>/dev/null | grep 1433 || echo "No hay conexiones activas a 1433"'))
