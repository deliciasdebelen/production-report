import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.1.79", username="administrador", password="GRW7czL3*")

print("Executing migration script inside the production web container...")
cmd = "echo 'GRW7czL3*' | sudo -S docker-compose -f /home/administrador/apps/production-report/docker-compose.yml run --rm web python scripts/migrate_sqlite_to_pg.py"
stdin, stdout, stderr = client.exec_command(cmd)

out = stdout.read().decode()
err = stderr.read().decode()

print("STDOUT:", out)
print("STDERR:", err)

client.close()
