import paramiko, os

HOST, USER, PASS = "192.168.1.79", "administrador", "GRW7czL3*"
REMOTE_DIR = "/home/administrador/apps/production-report"
LOCAL_BASE  = os.path.dirname(os.path.abspath(__file__))

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, 22, USER, PASS)
sftp = client.open_sftp()

files = [
    ("app/templates/support/management.html", REMOTE_DIR + "/app/templates/support/management.html"),
]
for local_rel, remote_path in files:
    sftp.put(os.path.join(LOCAL_BASE, local_rel), remote_path)
    print(f"Subido: {local_rel}")

sftp.close()

cmd = f"echo '{PASS}' | sudo -S docker-compose -f {REMOTE_DIR}/docker-compose.yml restart web 2>&1"
_, out, err = client.exec_command(cmd, timeout=60)
print(out.read().decode("ascii", errors="replace").strip())
client.close()
print("Listo.")
