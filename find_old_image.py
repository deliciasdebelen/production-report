import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.1.79", 22, "administrador", "GRW7czL3*")
cmd = "docker images --format '{{.ID}}|{{.CreatedAt}}|{{.Repository}}'"
stdin, stdout, stderr = client.exec_command(cmd)
for line in stdout.read().decode().splitlines():
    if "production-report-web" in line or "production-report" in line or "<none>" in line:
        print(line)
client.close()
