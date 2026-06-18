import paramiko, os

HOST, USER, PASS = "192.168.1.79", "administrador", "GRW7czL3*"
REMOTE_BASE = "/home/administrador/apps/production-report"
LOCAL_BASE  = os.path.dirname(os.path.abspath(__file__))

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, 22, USER, PASS)
sftp = client.open_sftp()

# 1. Migración DB: añadir columna status
cmd_migrate = (
    "echo '" + PASS + "' | sudo -S docker exec production-report-db psql -U app_user -d production_db -c "
    "\"ALTER TABLE project_cards ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'Por Hacer';\" 2>&1"
)
stdin, stdout, stderr = client.exec_command(cmd_migrate, timeout=20)
print("DB Migration:", stdout.read().decode("utf-8", errors="replace").strip())

# 2. Subir archivos modificados
files = [
    ("app/models.py",                              REMOTE_BASE + "/app/models.py"),
    ("app/routers/projects.py",                    REMOTE_BASE + "/app/routers/projects.py"),
    ("app/templates/projects/board.html",          REMOTE_BASE + "/app/templates/projects/board.html"),
    ("app/templates/projects/detail.html",         REMOTE_BASE + "/app/templates/projects/detail.html"),
]
for local_rel, remote_path in files:
    local_path = os.path.join(LOCAL_BASE, local_rel)
    sftp.put(local_path, remote_path)
    print(f"Subido: {local_rel}")

sftp.close()

# 3. Restart
cmd_restart = "echo '" + PASS + "' | sudo -S docker-compose -f " + REMOTE_BASE + "/docker-compose.yml restart web 2>&1"
stdin2, stdout2, stderr2 = client.exec_command(cmd_restart, timeout=60)
print("Restart:", stdout2.read().decode("ascii", errors="replace").strip())
client.close()
print("Done.")
