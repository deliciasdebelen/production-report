
import paramiko

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22
REMOTE_DIR = "/home/administrador/apps/production-report"

def run_remote():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        print(f"Connecting to {HOSTNAME}...")
        client.connect(HOSTNAME, port=PORT, username=USERNAME, password=PASSWORD)
        
        # Upload
        sftp = client.open_sftp()
        sftp.put("inspect_remote_ids.py", f"{REMOTE_DIR}/inspect_remote_ids_remote.py")
        sftp.close()
        
        # Exec
        print("Executing inspection...")
        client.exec_command(f"cd {REMOTE_DIR} && docker cp inspect_remote_ids_remote.py production-report:/app/inspect_remote_ids_remote.py")
        stdin, stdout, stderr = client.exec_command(f"docker exec production-report python /app/inspect_remote_ids_remote.py")
        
        print(stdout.read().decode())
        print(stderr.read().decode())

        # Cleanup
        # client.exec_command(f"rm {REMOTE_DIR}/inspect_remote_ids_remote.py")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    run_remote()
