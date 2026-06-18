import paramiko

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)

cmd = f"""docker ps --format '{{{{.Names}}}}' | grep db"""

stdin, stdout, stderr = client.exec_command(cmd)
out = stdout.read().decode()
db_name = out.strip()

cmd = f"""docker exec {db_name} psql -U app_user -d production_db -c "
CREATE TABLE IF NOT EXISTS audi_logs (
    id SERIAL PRIMARY KEY,
    report_text TEXT NOT NULL,
    status VARCHAR DEFAULT 'Generado',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);
CREATE INDEX IF NOT EXISTS ix_audi_logs_id ON audi_logs(id);
"
"""

stdin, stdout, stderr = client.exec_command(cmd)
out = stdout.read().decode()
err = stderr.read().decode()
print("OUT:", out)
if err: print("ERR:", err)

client.close()
