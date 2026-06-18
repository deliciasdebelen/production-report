import paramiko

HOST = "192.168.1.79"
SSH_USER = "administrador"
SSH_PASS = "GRW7czL3*"
REMOTE_BASE = "/home/administrador/apps/production-report"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=SSH_USER, password=SSH_PASS, timeout=30)

sftp = ssh.open_sftp()

# Leer docker-compose.yml
try:
    with sftp.file(f"{REMOTE_BASE}/docker-compose.yml", "r") as f:
        content = f.read().decode()
    print("=== docker-compose.yml ===")
    print(content)
except Exception as e:
    print(f"Error leyendo docker-compose.yml: {e}")

sftp.close()
ssh.close()
