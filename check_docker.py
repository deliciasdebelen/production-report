import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.79', username='administrador', password='GRW7czL3*')

cmd = "sudo -S docker ps"

stdin, stdout, stderr = client.exec_command(cmd)
stdin.write('GRW7czL3*\n')
stdin.flush()

print("OUT:", stdout.read().decode('utf-8'))
print("ERR:", stderr.read().decode('utf-8'))
client.close()
