import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.79', username='administrador', password='GRW7czL3*')

stdin, stdout, stderr = client.exec_command("find /home/administrador -name '*.db' -o -name '*.bak'")
print(stdout.read().decode())
if stderr:
    print(stderr.read().decode())

client.close()
