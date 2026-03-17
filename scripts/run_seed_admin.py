import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.1.79", username="administrador", password="GRW7czL3*")

print("Copying missing admin seed script to the server...")
sftp = client.open_sftp()
sftp.put("scripts/seed_master_admin.py", "/tmp/seed_master_admin.py")
sftp.close()

print("Executing seeding script on the production PG database...")
cmd_cp = "echo 'GRW7czL3*' | sudo -S docker cp /tmp/seed_master_admin.py production-report:/app/seed_master_admin.py"
client.exec_command(cmd_cp)

cmd1 = "echo 'GRW7czL3*' | sudo -S docker exec production-report python /app/seed_master_admin.py"
stdin, stdout, stderr = client.exec_command(cmd1)

print("STDOUT:", stdout.read().decode())
print("STDERR:", stderr.read().decode())

client.close()
