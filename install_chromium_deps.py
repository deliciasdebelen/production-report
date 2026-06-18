import paramiko, time

SSH_HOST = "192.168.1.79"
SSH_USER = "administrador"
SSH_PASS = "GRW7czL3*"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS)
print("Conectado.")

def run(cmd, timeout=180):
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors='replace')
    err = stderr.read().decode(errors='replace')
    combined = (out + err).strip()
    if combined: print("  =>", combined[:500])
    return out

# Install missing libs that chromium needs (libatk and more)
print("[1] Instalando libatk y dependencias del sistema...")
# Try apt with sudo via echo pipe
run("echo 'GRW7czL3*' | sudo -S apt-get install -y libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libgtk-3-0 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 2>&1 | tail -8")

print("[2] Verificando que las libs existan ahora...")
run("ldconfig -p | grep -E 'libatk|libgbm'")

print("[3] Probando lanzar chromium...")
run("PATH=$PATH:/home/administrador/.local/bin python3 -c \"import asyncio; from playwright.async_api import async_playwright; print('IMPORT OK')\"")

client.close()
print("Listo!")
