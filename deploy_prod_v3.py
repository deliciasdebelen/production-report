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
        tar.add("scripts", arcname="scripts", filter=filter_func)
        tar.add("requirements.txt", arcname="requirements.txt")
        tar.add("Dockerfile", arcname="Dockerfile")
        tar.add("docker-compose.yml", arcname="docker-compose.yml")
        tar.add(".dockerignore", arcname=".dockerignore")
        if os.path.exists("migrate_db.py"):
            tar.add("migrate_db.py", arcname="migrate_db.py")
        if os.path.exists("init_support_data.py"):
            tar.add("init_support_data.py", arcname="init_support_data.py")
        if os.path.exists("sync_profit_replica.py"):
            tar.add("sync_profit_replica.py", arcname="sync_profit_replica.py")
        
        # We don't need to add it explicitly if it's in app/ and app/ is added recursively.
        # But 'app' dir logic: tar.add("app", arcname="app", filter=filter_func)
        # So app/migrate_ai.py is added.

def deploy():
    try:
        tar_name = "deploy.tar.gz"
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
        # Chain commands to preserve Directory context
        print("Starting Deployment Sequence...")
        full_deployment_cmd = (
            f"cd {REMOTE_DIR} && "
            f"tar -xzf {tar_name} && "
            f"echo 'Building images...' && "
            f"docker-compose build && "
            f"echo 'Starting Services...' && "
            f"docker-compose up -d"
        )
        
        run_cmd(full_deployment_cmd)
        
        # Note: setup_remote_backups.py is designed to run locally on the server or via paramiko.
        # But we bundled it in 'scripts/'. If we run it via 'docker exec web', it needs paramiko installed in the container
        # OR we run it directly via the SSH client we already have open here.
        # The script uses paramiko to SSH into... localhost? No, the script expects to run from an external machine OR locally.
        # Let's check setup_remote_backups.py... it connects to HOSTNAME (192.168.1.79).
        # So it's meant to run from the DEPLOYMENT MACHINE (Laptop), not the server.
        
        # CORRECTING STRATEGY: Run setup_backups locally on the laptop after deployment.
        
        client.close()
        print("Deployment finished successfully.")
        
        # Run Backup Setup from Local
        try:
             import sys
             sys.path.append(os.getcwd())
             from scripts.setup_remote_backups import setup_backups
             setup_backups()
        except Exception as e:
             print(f"Warning: Backup setup failed locally: {e}")
        
        # Cleanup local
        if os.path.exists(tar_name):
            os.remove(tar_name)

    except Exception as e:
        print(f"Deployment Failed: {e}")

if __name__ == "__main__":
    deploy()
