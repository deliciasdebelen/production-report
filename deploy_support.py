import paramiko
import os

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22

FILES_TO_DEPLOY = [
    ("app/models.py", "/app/app/models.py"),
    ("app/main.py", "/app/app/main.py"),
    ("app/routers/support.py", "/app/app/routers/support.py"),
    ("app/templates/support/config.html", "/app/app/templates/support/config.html"),
    ("app/templates/support/confirm_ticket.html", "/app/app/templates/support/confirm_ticket.html")
]

def run():
    print(f"Connecting to {HOSTNAME}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
    sftp = client.open_sftp()
    
    print("Creating temp directory /tmp/support_patch")
    client.exec_command('mkdir -p /tmp/support_patch/app/routers')
    client.exec_command('mkdir -p /tmp/support_patch/app/templates/support')
    
    for local_path, container_path in FILES_TO_DEPLOY:
        full_local_path = os.path.join("../Projects/production-report", local_path)
        remote_tmp_path = "/tmp/support_patch/" + local_path
        print(f"Uploading {local_path} to {remote_tmp_path}...")
        sftp.put(full_local_path, remote_tmp_path)
        
        # Copy to container
        print(f"Copying to container {container_path}...")
        cmd = f'echo "{PASSWORD}" | sudo -S docker cp {remote_tmp_path} production-report:{container_path}'
        stdin, stdout, stderr = client.exec_command(cmd)
        err = stderr.read().decode().strip()
        if err and "Password:" not in err:
            print(f"Error copying {local_path}: {err}")
            
    sftp.close()
    
    print("Restarting production-report container...")
    cmd = f'echo "{PASSWORD}" | sudo -S docker restart production-report'
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode())
    
    client.close()
    print("Deployment completed!")

if __name__ == "__main__":
    run()
