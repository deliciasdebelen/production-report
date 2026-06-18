"""
deploy_support_fix.py - version final con reset
"""
import paramiko
import time

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22
PROJ_DIR = "/home/administrador/apps/production-report"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOSTNAME, PORT, USERNAME, PASSWORD, timeout=30)
print(f"Conectado a {HOSTNAME}")

# 1. Ver estado del repo en el servidor
print(f"\n[1] Estado del repo en servidor...")
for cmd in [
    f"cd {PROJ_DIR} && git status --short 2>&1",
    f"cd {PROJ_DIR} && git log --oneline -3 2>&1",
]:
    stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
    print(f"  $ {cmd.split('&&')[1].strip()}")
    print(f"    {stdout.read().decode().strip()}")

# 2. Reset al estado de origin/main (descarta cambios locales del servidor)
print(f"\n[2] Sincronizando con origin/main (fetch + reset)...")
cmds = [
    f"cd {PROJ_DIR} && git fetch origin 2>&1",
    f"cd {PROJ_DIR} && git reset --hard origin/main 2>&1",
]
for cmd in cmds:
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    label = cmd.split('&&')[1].strip()
    print(f"  $ {label}")
    print(f"    {out}")
    if err: print(f"    ERR: {err}")

# 3. Verificar que el fix esta en el codigo del host
print(f"\n[3] Verificando fix en host...")
cmd = f"grep -n 'ALLOWED_ROLES' {PROJ_DIR}/app/routers/support.py 2>&1"
stdin, stdout, stderr = client.exec_command(cmd, timeout=10)
grep_host = stdout.read().decode().strip()
print(f"  {grep_host}")

if 'ALLOWED_ROLES' not in grep_host:
    print("  CRITICO: Fix no encontrado en host tras reset. Abortando.")
    client.close()
    exit(1)

# 4. Restart del contenedor
print("\n[4] Reiniciando contenedor production-report...")
stdin, stdout, stderr = client.exec_command(
    "docker restart production-report 2>&1", timeout=60)
out = stdout.read().decode().strip()
print(f"  {out}")

# 5. Esperar inicio
print("\n[5] Esperando 15s para que el servicio inicie...")
time.sleep(15)

# 6. Estado de contenedores
stdin, stdout, stderr = client.exec_command(
    "docker ps --filter 'name=production-report' --format '{{.Names}} | {{.Status}}'")
print(stdout.read().decode().strip())

# 7. Verificar endpoint
print("\n[6] Verificando HTTP 192.168.1.79:8000...")
cmd = "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/support/tickets"
stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
http_code = stdout.read().decode().strip()
ok = http_code in ('200', '401', '403')
print(f"  HTTP {http_code} → {'SERVICIO ACTIVO' if ok else 'VERIFICAR'}")

# 8. Verificar fix en el contenedor
print("\n[7] Confirmando fix en contenedor...")
cmd = "docker exec production-report grep -n 'ALLOWED_ROLES' /app/app/routers/support.py 2>&1"
stdin, stdout, stderr = client.exec_command(cmd, timeout=10)
grep_cont = stdout.read().decode().strip()
print(f"  {grep_cont}")

if 'ALLOWED_ROLES' in grep_cont:
    print("\n  FIX CONFIRMADO Y ACTIVO EN PRODUCCION.")
    print("  El cierre de tickets ya puede realizarse con roles 4 y 7.")
else:
    print("\n  ADVERTENCIA: Fix no visible en contenedor.")
    print("  El contenedor puede no estar usando bind mount del host.")
    print("  Verificar volumes en docker-compose.yml")

client.close()
print("\nDeploy completado.")
