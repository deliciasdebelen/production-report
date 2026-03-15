import paramiko
import os

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
LOCAL_FILE = "scripts/remote_db_check_internal.py"
REMOTE_PATH = "/home/administrador/apps/production-report/scripts/remote_db_check_internal.py"

def run_check():
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOSTNAME, port=22, username=USERNAME, password=PASSWORD)
        
        sftp = client.open_sftp()
        sftp.put(LOCAL_FILE, REMOTE_PATH)
        sftp.close()
        
        # Run inside container
        # Note: 'scripts/' is mapped to '/app/scripts/' in the container if docker-compose maps it.
        # But wait, our docker-compose doesn't have volumes!
        # So we must COPY it into the container or use stdin.
        
        cmd_run = f"cat {REMOTE_PATH} | docker exec -i production-report python -"
        stdin, stdout, stderr = client.exec_command(cmd_run)
        print(stdout.read().decode())
        print(stderr.read().decode())
        
        client.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_check()
