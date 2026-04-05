import paramiko

HOST, USER, PASS = "192.168.1.79", "administrador", "GRW7czL3*"
REMOTE_DB = "/home/administrador/apps/production-report/production.db"

SCRIPT = f"""
import sqlite3
conn = sqlite3.connect('{REMOTE_DB}')
cur  = conn.cursor()

# Crear proyecto Homologacion si no existe
project_id = "homologacion-001"
exists = cur.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
if not exists:
    cur.execute("INSERT INTO projects (id, name, description, background) VALUES (?, ?, ?, ?)",
                (project_id, "Homologacion", "Proyecto inicial de homologacion de procesos", "#1e1b4b"))
    print(f"Proyecto Homologacion creado")
else:
    print(f"Proyecto ya existia")

# Vincular tableros
n = cur.execute("UPDATE project_boards SET project_id = ? WHERE project_id IS NULL", (project_id,)).rowcount
print(f"{{n}} tableros vinculados")

# Vincular etiquetas al proyecto
n2 = cur.execute("UPDATE project_labels SET project_id = ? WHERE project_id IS NULL", (project_id,)).rowcount
print(f"{{n2}} etiquetas migradas")

conn.commit()

# Estado final
print("Proyectos:", cur.execute("SELECT id, name FROM projects").fetchall())
print("Tableros por proyecto:", cur.execute("SELECT project_id, COUNT(*) FROM project_boards GROUP BY project_id").fetchall())
print("Etiquetas:", cur.execute("SELECT name, project_id FROM project_labels").fetchall())
conn.close()
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, 22, USER, PASS)
sftp = client.open_sftp()
with sftp.file("/tmp/seed_project.py", "w") as f:
    f.write(SCRIPT)
sftp.close()
stdin, stdout, stderr = client.exec_command("python3 /tmp/seed_project.py", timeout=20)
out = stdout.read().decode(errors="replace")
err = stderr.read().decode(errors="replace")
client.close()
print(out)
if err: print("ERR:", err)
