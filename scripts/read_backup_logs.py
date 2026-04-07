import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.79', username='administrador', password='GRW7czL3*')

print("=== BACKUP SCRIPT ===")
stdin, stdout, stderr = client.exec_command('cat /home/administrador/backup_production_db.sh')
print(stdout.read().decode())

print("=== BACKUP LOGS ===")
stdin, stdout, stderr = client.exec_command('tail -n 50 /home/administrador/backup.log')
print(stdout.read().decode())
print(stderr.read().decode())

client.close()
