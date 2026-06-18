import paramiko
import os
import tarfile

# Compress the app directory safely
tar_path = os.path.join(os.environ.get('TEMP', '/tmp'), 'deploy_sync_79.tar.gz')
print(f"Archiving 'app' directory to {tar_path}...")
with tarfile.open(tar_path, "w:gz") as tar:
    tar.add("app", arcname="app")

# Connect via paramiko
print("Connecting via SSH to 192.168.1.79...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.1.79", username="administrador", password="GRW7czL3*")

# Upload via SFTP
print("Uploading tarball...")
sftp = client.open_sftp()
sftp.put(tar_path, "/tmp/deploy_sync_79.tar.gz")
sftp.close()

# Extract and restart on the server
print("Extracting and restarting web container on production...")
cmd = "echo 'GRW7czL3*' | sudo -S tar -xzf /tmp/deploy_sync_79.tar.gz -C /home/administrador/apps/production-report/ && echo 'GRW7czL3*' | sudo -S docker-compose -f /home/administrador/apps/production-report/docker-compose.yml restart web"
stdin, stdout, stderr = client.exec_command(cmd)

out = stdout.read().decode()
err = stderr.read().decode()

print("STDOUT:", out)
print("STDERR:", err)

client.close()
print("Deployment to Production .79 Complete!")
