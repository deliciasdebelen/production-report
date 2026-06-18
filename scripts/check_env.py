import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.1.79", username="administrador", password="GRW7czL3*")

cmd = "echo 'GRW7czL3*' | sudo -S docker exec production-report env | grep DATABASE_URL"
stdin, stdout, stderr = client.exec_command(cmd)

print("STDOUT:", stdout.read().decode())
print("STDERR:", stderr.read().decode())

client.close()
