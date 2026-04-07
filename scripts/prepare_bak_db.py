import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.79', username='administrador', password='GRW7czL3*')

def run(cmd):
    print("Running:", cmd)
    stdin, stdout, stderr = client.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    print("OUT:", stdout.read().decode().strip())
    print("ERR:", stderr.read().decode().strip())
    print("Status:", exit_status)
    return exit_status

run('docker exec -i production-report-db psql -U app_user -d postgres -c "DROP DATABASE IF EXISTS production_db_bak;"')
run('docker exec -i production-report-db psql -U app_user -d postgres -c "CREATE DATABASE production_db_bak OWNER app_user;"')
run('zcat /home/administrador/backups/production-report/production_20260316_030001.sql.gz | docker exec -i production-report-db psql -U app_user -d production_db_bak')

client.close()
