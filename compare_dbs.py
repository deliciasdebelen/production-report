"""
Comparar las dos BDs encontradas: /app/production.db vs /app/data/production.db
"""
import paramiko, time

HOST = "192.168.1.79"
SSH_USER = "administrador"
SSH_PASS = "GRW7czL3*"

TABLES = [
    "logistics_dispatch", "support_tickets", "production_reports",
    "production_planning", "logistics_reception_merchandise",
    "logistics_reception_production", "inventory_headers",
    "inventory_lines", "users", "roles",
]

py_check = """
import sqlite3

dbs = ['/app/production.db', '/app/data/production.db']
tables = {TABLES}

for db_path in dbs:
    print(f'=== {{db_path}} ===')
    try:
        conn = sqlite3.connect(db_path)
        for t in tables:
            try:
                n = conn.execute(f'SELECT COUNT(*) FROM {{t}}').fetchone()[0]
                print(f'{{t}}|{{n}}')
            except Exception as e:
                print(f'{{t}}|NO_EXISTE')
        conn.close()
    except Exception as e:
        print(f'ERROR abriendo DB: {{e}}')
""".format(TABLES=str(TABLES))

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=SSH_USER, password=SSH_PASS, timeout=30)

sftp = ssh.open_sftp()
with sftp.file("/tmp/compare_db.py", "w") as f:
    f.write(py_check)
sftp.close()

cmd = (
    f"echo '{SSH_PASS}' | sudo -S bash -c "
    f"'docker cp /tmp/compare_db.py production-report:/tmp/compare_db.py "
    f"&& docker exec production-report python3 /tmp/compare_db.py'"
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

current_db = ""
print(f"\n{'Tabla':<42} {'prod.db':>10} {'data/prod.db':>14}")
print("-" * 70)

db_data = {}
for line in decoded.splitlines():
    line = line.strip().replace("\r", "")
    if line.startswith("=== "):
        current_db = line.replace("=== ", "").replace(" ===", "").strip()
        db_data[current_db] = {}
    elif "|" in line and current_db:
        parts = line.split("|", 1)
        if len(parts) == 2:
            db_data[current_db][parts[0].strip()] = parts[1].strip()

for t in TABLES:
    v1 = db_data.get("/app/production.db", {}).get(t, "?")
    v2 = db_data.get("/app/data/production.db", {}).get(t, "?")
    flag = "  <-- DIFERENCIA" if v1 != v2 and v1 != "?" and v2 != "?" else ""
    print(f"{t:<42} {v1:>10} {v2:>14}{flag}")
