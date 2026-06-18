import paramiko
import os
import sys
import time

# Configuration
HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22
REMOTE_APP_DIR = "/home/administrador/apps/production-report"
LOCAL_DB_PATH = "production.db"
REMOTE_DB_PATH = f"{REMOTE_APP_DIR}/production.db"

def restore_db():
    if not os.path.exists(LOCAL_DB_PATH):
        print(f"Error: Local database '{LOCAL_DB_PATH}' not found.")
        sys.exit(1)

    print(f"Starting Database Restore to {HOSTNAME}...")

    try:
        # Establish SSH Connection
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
        
        # 1. Stop the container to release file locks
        print("Stopping remote container 'production-report'...")
        stdin, stdout, stderr = client.exec_command(f"cd {REMOTE_APP_DIR} && docker-compose stop web")

        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            print(f"Error stopping container: {stderr.read().decode()}")
            # Proceeding anyway usually risks file in use error, but we try.
        else:
            print("Container stopped.")

        # 2. Upload the database
        print(f"Uploading {LOCAL_DB_PATH} to {REMOTE_DB_PATH}...")
        sftp = client.open_sftp()
        sftp.put(LOCAL_DB_PATH, REMOTE_DB_PATH)
        sftp.close()
        print("Upload complete.")

        # 3. Restart the container
        print("Restarting remote container...")
        stdin, stdout, stderr = client.exec_command(f"cd {REMOTE_APP_DIR} && docker-compose start web")

        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            print(f"Error starting container: {stderr.read().decode()}")
        else:
            print("Container restarted successfully.")
            
        client.close()
        print("\nDatabase restore completed successfully!")

    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    restore_db()
