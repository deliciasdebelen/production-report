
import paramiko
import os
import time

# Sync with deploy_prod.py settings
HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22
REMOTE_DIR = "/home/administrador/apps/production-report"

def diagnose():
    try:
        print(f"Connecting to {HOSTNAME}...")
        transport = paramiko.Transport((HOSTNAME, PORT))
        transport.connect(username=USERNAME, password=PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        script_name = "remote_query_script.py"
        print(f"Uploading {script_name} to app/...")
        # Upload to app/ subdirectory which is volume mounted
        sftp.put(script_name, f"{REMOTE_DIR}/app/{script_name}")
        sftp.close()
        transport.close()
        
        # Execute Remote Commands
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
        
        # Run DB Diagnostic
        cmd_db = f"cd {REMOTE_DIR} && docker-compose exec -T web python app/{script_name}"
        print(f"Executing DB Check: {cmd_db}")
        stdin, stdout, stderr = client.exec_command(cmd_db)
        print("\n--- DB CHECK OUTPUT ---")
        print(stdout.read().decode())
        err = stderr.read().decode()
        if err: print(f"STDERR: {err}")
        print("--- END DB CHECK ---\n")
        
        # Check All Files
        cmd_ls = f"ls -la {REMOTE_DIR}"
        print(f"Executing File Listing: {cmd_ls}")
        stdin, stdout, stderr = client.exec_command(cmd_ls)
        print("\n--- HOST FILE LISTING ---")
        print(stdout.read().decode())
        
        # Stream output
        print("\n--- REMOTE OUTPUT START ---")
        print(stdout.read().decode())
        err = stderr.read().decode()
        if err:
            print(f"STDERR: {err}")
        print("--- REMOTE OUTPUT END ---\n")
            
        client.close()

    except Exception as e:
        print(f"Diagnostic Failed: {e}")

if __name__ == "__main__":
    diagnose()
