import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.79', username='administrador', password='GRW7czL3*')

cmd = "sudo -S docker exec production-report-db psql -U openpg -d production_db -c \"SELECT id, code, attachment_url FROM support_tickets WHERE attachment_url IS NOT NULL ORDER BY id DESC LIMIT 5;\""

stdin, stdout, stderr = client.exec_command(cmd)
stdin.write('GRW7czL3*\n')
stdin.flush()

print("OUT:", stdout.read().decode('utf-8'))
print("ERR:", stderr.read().decode('utf-8'))
client.close()
