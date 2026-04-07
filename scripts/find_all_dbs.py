import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.79', username='administrador', password='GRW7czL3*')

stdin, stdout, stderr = client.exec_command('find / -name "production.db" 2>/dev/null')
print("Found databases on .79:")
print(stdout.read().decode())
client.close()
