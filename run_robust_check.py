import paramiko
import sys
import os

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22
REMOTE_DIR = "/home/administrador/apps/production-report"

def run_robust_check():
    print(f"Connecting to {HOSTNAME}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
        
        # Upload script
        sftp = client.open_sftp()
        local_path = "migrate_planning_debug.py"
        remote_path = f"{REMOTE_DIR}/migrate_planning_debug.py"
        print(f"Uploading {local_path} to {remote_path}...")
        sftp.put(local_path, remote_path)
        sftp.close()
        
        # Run script inside container via mount
        cmd = (
            f"cd {REMOTE_DIR} && "
            f"docker-compose run -v {remote_path}:/app/migrate_planning_debug.py --rm web python /app/migrate_planning_debug.py"
        )
        
        print(f"Executing: {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd)
        
        # Stream Output
        while True:
            line = stdout.readline()
            if not line: break
            print(line.strip())
            
        print("STDERR:", stderr.read().decode())
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    run_robust_check()
