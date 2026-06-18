import paramiko

SSH_HOST = "192.168.1.79"
SSH_USER = "administrador"
SSH_PASS = "GRW7czL3*"

print("Conectando a 192.168.1.79...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS)

def run_cmd(cmd):
    print(f"Ejecutando: {cmd}")
    _, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode(errors='replace')
    err = stderr.read().decode(errors='replace')
    if out: print("  STDOUT:", out.strip())
    if err: print("  STDERR:", err.strip())

run_cmd("echo 'GRW7czL3*' | sudo -S apt-get update")
run_cmd("echo 'GRW7czL3*' | sudo -S apt-get install -y libasound2t64")

client.close()
print("Listo.")
