import paramiko

SSH_HOST = "192.168.1.79"
SSH_USER = "administrador"
SSH_PASS = "GRW7czL3*"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS)

def run(cmd):
    print(f"Run: {cmd[:100]}...")
    _, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode(errors='replace')
    err = stderr.read().decode(errors='replace')
    if out: print("  STDOUT:", out.strip()[:600])
    if err: print("  STDERR:", err.strip()[:600])

deps = (
    "libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 "
    "libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 "
    "libgbm1 libasound2t64 libpango-1.0-0 libcairo2"
)
try:
    run(f"echo 'GRW7czL3*' | sudo -S apt-get install -y {deps}")
    print("Done installing deps.")
    run("python3 -m playwright install-deps chromium")
except Exception as e:
    print("Error:", e)

client.close()
