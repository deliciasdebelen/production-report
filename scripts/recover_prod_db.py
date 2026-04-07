import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.79', username='administrador', password='GRW7czL3*')

def run_cmd(cmd):
    print(f"Executing: {cmd}")
    stdin, stdout, stderr = client.exec_command(f"echo 'GRW7czL3*' | sudo -S {cmd}")
    status = stdout.channel.recv_exit_status()
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out: print("OUT:", out)
    if err: print("ERR:", err)
    return status

# 1. Stop the web container so it disconnects from Postgres
run_cmd("docker stop production-report-web")

# 2. Terminate all active backend connections forcefully to allow dropdb
kill_conn_sql = "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = 'production_db' AND pid <> pg_backend_pid();"
run_cmd(f'docker exec -i production-report-db psql -U app_user -d postgres -c "{kill_conn_sql}"')

# 3. Drop and Create Database
run_cmd("docker exec -i production-report-db dropdb -U app_user production_db")
run_cmd("docker exec -i production-report-db createdb -U app_user -O app_user production_db")

# 4. Restore the perfect backup from Feb -> March 16th
print("Restoring...")
# zcat prints to stdout, pipe to docker exec
stdin, stdout, stderr = client.exec_command("zcat /home/administrador/backups/production-report/production_20260316_030001.sql.gz | docker exec -i production-report-db psql -U app_user -d production_db")
status = stdout.channel.recv_exit_status()
print(f"Restore finished with exit code {status}")
if status != 0:
    print(stderr.read().decode())

# 5. Bring application back online
run_cmd("docker start production-report-web")

print("Recovery Sequence Complete.")
client.close()
