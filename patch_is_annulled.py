import paramiko
import os

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22
REMOTE_DIR = "/home/administrador/apps/production-report"

# We pass this python script string directly into the container
db_patch_script = """
import sqlite3
import sys

print("Iniciando parche manual de base de datos SQLite...")
try:
    conn = sqlite3.connect('/app/production.db')
    cursor = conn.cursor()
    # Check if is_annulled exists to avoid double-alter crash
    cursor.execute("PRAGMA table_info(logistics_dispatch)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if 'is_annulled' not in columns:
        print("La columna 'is_annulled' no existe. Anadiendola ahora...")
        cursor.execute("ALTER TABLE logistics_dispatch ADD COLUMN is_annulled BOOLEAN DEFAULT 0;")
        conn.commit()
        print("Columna 'is_annulled' agregada exitosamente.")
    else:
        print("La columna 'is_annulled' ya existe.")
        
    conn.close()
    print("Parche de base de datos finalizado.")
except Exception as e:
    print(f"Error parseando BD: {e}")
    sys.exit(1)
"""

with open("temp_db_patch.py", "w") as f:
    f.write(db_patch_script)

try:
    print(f"Connecting to {HOSTNAME}...")
    transport = paramiko.Transport((HOSTNAME, PORT))
    transport.connect(username=USERNAME, password=PASSWORD)
    sftp = paramiko.SFTPClient.from_transport(transport)
    
    print("Uploading temp_db_patch.py...")
    sftp.put("temp_db_patch.py", f"{REMOTE_DIR}/temp_db_patch.py")
    sftp.close()
    transport.close()
    
    # Execute Remote Commands
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
    
    def run_cmd(cmd_str):
        print(f"Executing: {cmd_str}")
        stdin, stdout, stderr = client.exec_command(cmd_str)
        out = stdout.read().decode()
        err = stderr.read().decode()
        if out: print(out)
        if err: print(f"STDERR: {err}")
        return out, err

    run_cmd(f"cd {REMOTE_DIR} && docker cp temp_db_patch.py production-report:/app/temp_db_patch.py")
    run_cmd("docker exec production-report python temp_db_patch.py")
    run_cmd(f"cd {REMOTE_DIR} && rm temp_db_patch.py") # cleanup

    client.close()
    print("Patch applied to production.db.")
    
    if os.path.exists("temp_db_patch.py"):
        os.remove("temp_db_patch.py")

except Exception as e:
    print(f"Deployment Patch Failed: {e}")
