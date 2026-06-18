import paramiko

HOST, USER, PASS = "192.168.1.79", "administrador", "GRW7czL3*"
REMOTE_DIR = "/home/administrador/apps/production-report"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, 22, USER, PASS)

print("--- DB Attachments ---")
cmd = f"cd {REMOTE_DIR} && sqlite3 production.db \"SELECT id, code, attachment_url FROM support_tickets WHERE attachment_url IS NOT NULL;\""
stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode())

print("--- Directory Listing ---")
cmd = f"ls -la {REMOTE_DIR}/app/static/up/support"
stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode())

client.close()
