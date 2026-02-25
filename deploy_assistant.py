import paramiko
import os
import tarfile
from datetime import datetime

# Configuration
HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22
REMOTE_DIR = "/home/administrador/apps/production-report"
CONTAINER_NAME = "production-report"

def create_tarball(output_filename):
    print(f"Creating tarball {output_filename}...")
    with tarfile.open(output_filename, "w:gz") as tar:
        # Exclude patterns
        excludes = [
            '.git', '__pycache__', 'venv', '.env', '.vscode', 
            'deploy.tar.gz', 'production.db' # Do not overwrite DB
        ]
        
        def filter_func(tarinfo):
            for excl in excludes:
                if excl in tarinfo.name:
                    return None
            return tarinfo

        tar.add("app", arcname="app", filter=filter_func)
        # Include migrate_db if needed, but not critical for new tables handled by create_all

def deploy():
    try:
        tar_name = "deploy_assistant.tar.gz"
        create_tarball(tar_name)
        
        print(f"Connecting to {HOSTNAME}...")
        transport = paramiko.Transport((HOSTNAME, PORT))
        transport.connect(username=USERNAME, password=PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        print(f"Uploading {tar_name}...")
        sftp.put(tar_name, f"{REMOTE_DIR}/{tar_name}")
        sftp.close()
        transport.close()
        
        # Execute Remote Commands
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
        
        # Helper to run command
        def run_cmd(cmd_str):
            print(f"Executing: {cmd_str}")
            stdin, stdout, stderr = client.exec_command(cmd_str)
            out = stdout.read().decode()
            err = stderr.read().decode()
            if out: print(out)
            if err: print(f"STDERR: {err}")
            return out, err

        # Chain commands to preserve Directory context
        full_deployment_cmd = (
            f"cd {REMOTE_DIR} && "
            f"tar -xzf {tar_name} && "
            f"echo 'Restarting container...' && "
            f"docker-compose restart web && "
            f"sleep 5 && " # Wait for startup
            f"echo 'Deployment Complete'"
        )
        
        run_cmd(full_deployment_cmd)
            
        client.close()
        print("Deployment finished successfully.")
        
        # Cleanup local
        if os.path.exists(tar_name):
            os.remove(tar_name)

    except Exception as e:
        print(f"Deployment Failed: {e}")

if __name__ == "__main__":
    deploy()
