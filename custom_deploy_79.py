import paramiko
import os

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22
REMOTE_APP_DIR = "/home/administrador/apps/production-report/app"

files_to_sync = [
    "app/routers/support.py",
    "app/templates/support/management.html",
]

def deploy():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("Connecting to", HOSTNAME)
    client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
    
    sftp = client.open_sftp()
    
    for f in files_to_sync:
        local_path = os.path.join(os.getcwd(), f)
        # Create corresponding remote path
        # Normalize to POSIX
        f_posix = f.replace('\\', '/')
        # `f_posix` starts with "app/", so remote path is replacing "app/" with REMOTE_APP_DIR
        remote_path = f_posix.replace("app/", REMOTE_APP_DIR + "/", 1)
        
        if os.path.exists(local_path):
            print(f"Uploading {local_path} to {remote_path}")
            sftp.put(local_path, remote_path)
            
    sftp.close()
    
    print("Restarting web container...")
    # Executing the restart
    cmd = f"echo '{PASSWORD}' | sudo -S docker-compose -f /home/administrador/apps/production-report/docker-compose.yml restart web"
    stdin, stdout, stderr = client.exec_command(cmd)
    
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    client.close()
    print("Deployment completed!")

if __name__ == '__main__':
    deploy()
