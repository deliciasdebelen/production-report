import paramiko
import os
import tarfile

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)

    print("Creating temp recovery container from image 426a5e979317 (2026-03-06)...")
    client.exec_command("docker rm -f temp_recovery")
    stdin, stdout, stderr = client.exec_command("docker create --name temp_recovery 426a5e979317")
    out = stdout.read().decode().strip()
    if out: print("Container ID:", out)
    err = stderr.read().decode().strip()
    if err: print("Error:", err)

    print("Copying files from container to /tmp/app_recovery_dir...")
    client.exec_command("rm -rf /tmp/app_recovery_dir")
    stdin, stdout, stderr = client.exec_command("docker cp temp_recovery:/app /tmp/app_recovery_dir")
    stdout.read() # wait

    print("Tarring directories on remote...")
    stdin, stdout, stderr = client.exec_command("cd /tmp/app_recovery_dir && tar -czf /tmp/recovery_backup.tar.gz .")
    stdout.read() # wait
    
    # Download
    print("Downloading recovery_backup.tar.gz via SFTP...")
    transport = paramiko.Transport((HOSTNAME, PORT))
    transport.connect(username=USERNAME, password=PASSWORD)
    sftp = paramiko.SFTPClient.from_transport(transport)
    sftp.get("/tmp/recovery_backup.tar.gz", "recovery_backup.tar.gz")
    sftp.close()
    transport.close()

    print("Cleaning up remote resources...")
    client.exec_command("docker rm -f temp_recovery")
    client.exec_command("rm -rf /tmp/app_recovery_dir")
    client.exec_command("rm /tmp/recovery_backup.tar.gz")
    client.close()
    print("Recovery backup downloaded successfully.")

except Exception as e:
    print(f"Recovery script failed: {e}")
