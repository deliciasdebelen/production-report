import paramiko
import os

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22
REMOTE_DIR = "/home/administrador/apps/production-report"
CONTAINER_NAME = "production-report" # Or 'web' service name for docker-compose exec

def run_remote_test():
    try:
        # 1. Upload Script
        transport = paramiko.Transport((HOSTNAME, PORT))
        transport.connect(username=USERNAME, password=PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        local_script = "debug_remote_articles.py"
        remote_script = f"{REMOTE_DIR}/{local_script}"
        
        print(f"Uploading {local_script} to {remote_script}...")
        sftp.put(local_script, remote_script)
        sftp.close()
        transport.close()
        
        # 2. Execute in Container
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
        
        # We need to copy into container or run from volume if mounted
        # The 'app' dir is mounted to /app/app. The root of project is mounted?
        # In docker-compose.yml:
        # - ./app:/app/app
        # - ./data:/app/data
        # But debug_remote_articles.py is in root of remote_dir.
        # Let's copy it into the container first.
        
        cmd = f"docker cp {remote_script} {CONTAINER_NAME}:/app/debug_remote_articles.py && docker exec {CONTAINER_NAME} python /app/debug_remote_articles.py"
        
        print(f"Executing: {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd)
        
        print("--- STDOUT ---")
        print(stdout.read().decode())
        print("--- STDERR ---")
        print(stderr.read().decode())
        
        client.close()

    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    run_remote_test()
