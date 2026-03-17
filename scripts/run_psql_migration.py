import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.1.79", username="administrador", password="GRW7czL3*")

print("Generating SQL dump from SQLite and importing it to PostgreSQL via psql...")

bash_script = """
cd /home/administrador/apps/production-report
# 1. Dump SQLite data using the python image (which has sqlite3)
docker-compose -f docker-compose.yml run --rm web bash -c "sqlite3 /app/production.db.live '.dump'" > dump.sql

# 2. Filter out SQLite specific commands and only keep INSERTs
grep -v "^PRAGMA" dump.sql | grep -v "^BEGIN" | grep -v "^COMMIT" | grep -v "^CREATE" | grep -v "^DELETE FROM sqlite_sequence" | grep -v "sqlite_sequence" > data_only.sql

# 3. Import data_only.sql using psql
docker-compose -f docker-compose.yml exec -T db psql -U app_user -d production_db < data_only.sql
"""

cmd = f"echo 'GRW7czL3*' | sudo -S bash -c '{bash_script}'"
stdin, stdout, stderr = client.exec_command(cmd)

out = stdout.read().decode()
err = stderr.read().decode()

print("STDOUT:", out)
print("STDERR:", err)

client.close()
