import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.1.79", username="administrador", password="GRW7czL3*")

print("Executing pgloader in a temporary container connecting to the production database...")
# Use pgloader to migrate directly from the SQLite file to PostgreSQL without python dependencies
cmd = "echo 'GRW7czL3*' | sudo -S docker run --rm --network production-report_app-network -v /home/administrador/apps/production-report/production.db.live:/data/production.db.live dimitri/pgloader pgloader /data/production.db.live postgresql://app_user:production_password@db:5432/production_db"

stdin, stdout, stderr = client.exec_command(cmd)

out = stdout.read().decode()
err = stderr.read().decode()

print("STDOUT:", out)
print("STDERR:", err)

client.close()
