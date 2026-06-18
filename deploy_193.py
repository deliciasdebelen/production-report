import paramiko
import os
import tarfile
from datetime import datetime

# Configuration
HOSTNAME = "192.168.1.193"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22
REMOTE_DIR = "/home/administrador/apps/production-report"
CONTAINER_NAME = "production-report"

def create_tarball(output_filename):
    print(f"Creating tarball {output_filename}...")
    with tarfile.open(output_filename, "w:gz") as tar:
        excludes = [
            '.git', '__pycache__', 'venv', '.env', '.vscode', 
            'deploy.tar.gz', 'production.db'
        ]
        
        def filter_func(tarinfo):
            for excl in excludes:
                if excl in tarinfo.name:
                    return None
            return tarinfo

        tar.add("app", arcname="app", filter=filter_func)
        tar.add("scripts", arcname="scripts", filter=filter_func)
        tar.add("requirements.txt", arcname="requirements.txt")
        tar.add("Dockerfile", arcname="Dockerfile")
        tar.add("docker-compose.yml", arcname="docker-compose.yml")
        tar.add(".dockerignore", arcname=".dockerignore")

        # Explicitly include files needed by Docker that might be missing on a fresh server
        for extra in ["custom_openssl.cnf", "migrate_db.py", "init_support_data.py", "migrate_ai.py"]:
            if os.path.exists(extra):
                tar.add(extra, arcname=extra)

def deploy():
    try:
        tar_name = "deploy.tar.gz"
        create_tarball(tar_name)
        
        print(f"Connecting to {HOSTNAME}...")
        transport = paramiko.Transport((HOSTNAME, PORT))
        transport.connect(username=USERNAME, password=PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        # Test if remote dir exists
        try:
             sftp.stat(REMOTE_DIR)
        except IOError:
             print(f"Directory {REMOTE_DIR} does not exist. Creating...")
             # sftp doesn't have mkdir -p, but we'll try basic or just fail and create via ssh
             
        print(f"Uploading {tar_name}...")
        sftp.put(tar_name, f"{REMOTE_DIR}/{tar_name}")
        sftp.close()
        transport.close()
        
        # Execute Remote Commands
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
        
        def run_cmd(cmd_str):
            print(f"Executing: {cmd_str}")
            stdin, stdout, stderr = client.exec_command(cmd_str)
            out = stdout.read().decode()
            err = stderr.read().decode()
            if out: print(out)
            if err: print(f"STDERR: {err}")
            return out, err

        print("Starting Deployment Sequence...")
        full_deployment_cmd = (
            f"cd {REMOTE_DIR} && "
            f"tar -xzf {tar_name} && "
            f"echo 'Building images...' && "
            f"docker compose build && "
            f"echo 'Starting Services...' && "
            f"docker compose up -d"
        )
        
        run_cmd(full_deployment_cmd)
        
        client.close()
        print("Deployment finished successfully.")
        
        if os.path.exists(tar_name):
            os.remove(tar_name)

    except Exception as e:
        print(f"Deployment Failed: {e}")

if __name__ == "__main__":
    deploy()
