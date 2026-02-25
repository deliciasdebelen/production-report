import paramiko
import os
import tarfile
import time

# Configuration
HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22
REMOTE_DIR = "/home/administrador/apps/production-report"

def create_update_package(output_filename):
    print(f"Creating update package {output_filename}...")
    with tarfile.open(output_filename, "w:gz") as tar:
        # Core App
        tar.add("app", arcname="app")
        # Migration Script
        tar.add("migrate_inventory_dept.py", arcname="migrate_inventory_dept.py")
        
def deploy():
    try:
        tar_name = "update_inventory.tar.gz"
        create_update_package(tar_name)
        
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
        
        def run_cmd(cmd_str):
            print(f"Executing: {cmd_str}")
            stdin, stdout, stderr = client.exec_command(cmd_str)
            # Wait for command to finish
            exit_status = stdout.channel.recv_exit_status() 
            out = stdout.read().decode()
            err = stderr.read().decode()
            if out: print(out)
            if err: print(f"STDERR: {err}")
            return exit_status
            
        # 1. Unpack
        print("--- Unpacking Code ---")
        run_cmd(f"cd {REMOTE_DIR} && tar -xzf {tar_name}")
        
        # 2. Run Migration inside Container
        print("--- Copying Migration Script to Container ---")
        # Copy file from Host to Container (since it's not mounted in root)
        run_cmd(f"cd {REMOTE_DIR} && docker cp migrate_inventory_dept.py production-report:/app/")
        
        print("--- Running Migration ---")
        # Execute using docker exec (simpler than compose for single command after cp)
        cmd_migrate = "docker exec production-report python migrate_inventory_dept.py"
        status = run_cmd(cmd_migrate)
        
        if status != 0:
            print("Migration failed! Aborting restart.")
            return

        # 3. Restart Service
        print("--- Restarting Service ---")
        run_cmd(f"cd {REMOTE_DIR} && docker-compose restart web")
            
        client.close()
        print("Deployment finished successfully.")
        
        # Cleanup local
        if os.path.exists(tar_name):
            os.remove(tar_name)

    except Exception as e:
        print(f"Deployment Failed: {e}")

if __name__ == "__main__":
    deploy()
