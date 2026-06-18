"""
Investigar anomalia: support_tickets muestra 1 en contenedor vs 26 via API
"""
import paramiko, time

HOST = "192.168.1.79"
SSH_USER = "administrador"
SSH_PASS = "GRW7czL3*"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=SSH_USER, password=SSH_PASS, timeout=30)

# Script para encontrar el archivo DB real que usa la app
py_check = """
import sqlite3, os

# Buscar archivos .db en el contenedor
for root, dirs, files in os.walk('/'):
    for f in files:
        if f.endswith('.db'):
            full = os.path.join(root, f)
            try:
                sz = os.path.getsize(full)
                print(f'DB|{full}|{sz}')
            except:
                pass

# Consultar la BD que usa la app (via DATABASE_URL env)
import os as _os
db_url = _os.environ.get('DATABASE_URL', '')
print(f'DBURL|{db_url}')

# Contar en cada .db encontrado
paths = []
for root, dirs, files in os.walk('/'):
    for f in files:
        if f.endswith('.db'):
            paths.append(os.path.join(root, f))

for p in paths:
    try:
        conn = sqlite3.connect(p)
        c = conn.execute("SELECT COUNT(*) FROM support_tickets")
        n = c.fetchone()[0]
        print(f'COUNT|{p}|{n}')
        conn.close()
    except:
        pass
"""

sftp = ssh.open_sftp()
with sftp.file("/tmp/find_db.py", "w") as f:
    f.write(py_check)
sftp.close()

cmd = (
    f"echo '{SSH_PASS}' | sudo -S "
    f"bash -c 'docker cp /tmp/find_db.py production-report:/tmp/find_db.py "
    f"&& docker exec production-report python3 /tmp/find_db.py'"
)

chan = ssh.get_transport().open_session()
chan.get_pty()
chan.exec_command(cmd)
output = b""
deadline = time.time() + 30
while time.time() < deadline:
    if chan.recv_ready():
        output += chan.recv(8192)
    if chan.exit_status_ready():
        time.sleep(0.5)
        while chan.recv_ready():
            output += chan.recv(8192)
        break
    time.sleep(0.1)
ssh.close()

decoded = output.decode(errors="replace")
print("\n=== ARCHIVOS DB ENCONTRADOS ===")
for line in decoded.splitlines():
    line = line.strip().replace("\r", "")
    if line.startswith("DB|") or line.startswith("DBURL|") or line.startswith("COUNT|"):
        print(line)
