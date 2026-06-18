import paramiko, os

HOST = "192.168.1.79"
USER = "administrador"
PASS = "GRW7czL3*"
LOCAL = r"c:\Users\ovargas\Projects\production-report\app\templates\projects\board.html"
REMOTE = "/home/administrador/apps/production-report/app/templates/projects/board.html"

# Verify local is clean
with open(LOCAL, encoding="utf-8") as f:
    content = f.read()

n_defs = content.count("async function deleteList")
has_confirm = "window.confirm" in content
print(f"deleteList defs: {n_defs}  |  has window.confirm: {has_confirm}")

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, 22, USER, PASS)

sftp = c.open_sftp()
sftp.put(LOCAL, REMOTE)
sftp.close()
print("board.html subido")

_, out, _ = c.exec_command(f'echo "{PASS}" | sudo -S docker restart production-report 2>&1', timeout=60)
resultado = out.read().decode("ascii", errors="replace").strip()
print("Restart:", resultado)

# Verificar en servidor
_, out2, _ = c.exec_command(
    f"grep -c 'deleteList' {REMOTE} && grep -c 'window.confirm' {REMOTE} || echo '0'", timeout=10
)
counts = out2.read().decode().strip()
print("Ocurrencias en servidor (deleteList, confirm):", counts)

c.close()
print("Listo.")
