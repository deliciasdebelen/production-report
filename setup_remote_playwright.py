import paramiko, time
from pathlib import Path

SSH_HOST = "192.168.1.79"
SSH_USER = "administrador"
SSH_PASS = "GRW7czL3*"

def run(client, cmd, timeout=120):
    print(f"  > {cmd[:80]}")
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors='replace')
    err = stderr.read().decode(errors='replace')
    if out.strip(): print("   OUT:", out.strip()[:400])
    if err.strip(): print("   ERR:", err.strip()[:400])
    return out

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS)
print("Conectado a", SSH_HOST)

# Check Python environment
run(client, "which python3 && python3 --version")
run(client, "pip3 --version || python3 -m pip --version")
# Install in user space bypassing PEP 668
print("\nInstalando playwright con --break-system-packages...")
run(client, "pip3 install playwright --break-system-packages --quiet 2>&1 | tail -5", timeout=120)
print("Instalando chromium...")
run(client, "python3 -m playwright install chromium 2>&1 | tail -5", timeout=180)
print("Instalando dependencias del sistema de chromium...")
run(client, "python3 -m playwright install-deps chromium 2>&1 | tail -10", timeout=180)
print("Verificando playwright:")
run(client, "python3 -c \"from playwright.async_api import async_playwright; print('OK')\"")

client.close()
print("\nListo - Ahora corre el script de captura!")
