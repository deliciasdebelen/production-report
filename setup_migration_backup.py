import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.79', username='administrador', password='GRW7czL3*', timeout=10)

cron_cmd = '30 17 * * * cp /home/administrador/apps/production-report/production.db /home/administrador/production_db_backup_pre_migration.db'
setup_cmd = f'(crontab -l 2>/dev/null | grep -v "production_db_backup_pre_migration"; echo "{cron_cmd}") | crontab -'
stdin, stdout, stderr = client.exec_command(setup_cmd)
err = stderr.read().decode()
out = stdout.read().decode()
if err: print('ERR:', err)
if out: print('OUT:', out)
print('Cron job scheduled on 192.168.1.79')
client.close()
