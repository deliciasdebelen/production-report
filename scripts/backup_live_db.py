import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.1.79", username="administrador", password="GRW7czL3*")

print("Connected. Backing up production.db...")
stdin, stdout, stderr = client.exec_command("echo 'GRW7czL3*' | sudo -S cp /home/administrador/apps/production-report/production.db /home/administrador/apps/production-report/production.db.bak_20260316")

out = stdout.read().decode()
err = stderr.read().decode()

print("STDOUT:", out)
print("STDERR:", err)

# Also stop the web container to ensure the DB file is static before we download and migrate
print("Stopping web container to freeze DB...")
stdin, stdout, stderr = client.exec_command("echo 'GRW7czL3*' | sudo -S docker-compose -f /home/administrador/apps/production-report/docker-compose.yml stop web")
print(stdout.read().decode())

print("Downloading the live database for FK patching...")
sftp = client.open_sftp()
sftp.get("/home/administrador/apps/production-report/production.db", "production.db.live")
sftp.close()

client.close()
print("Backup, Stop, and Download complete.")
