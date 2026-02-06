
import paramiko
import time

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
        
        # 1. Upload test script
        sftp = client.open_sftp()
        local_file = "test_id_reset.py"
        remote_file = f"{REMOTE_DIR}/test_id_reset_remote.py"
        print(f"Uploading {local_file} to {remote_file}...")
        sftp.put(local_file, remote_file)
        sftp.close()
        
        # 2. Exec inside Docker
        # We need to copy it into the container or assume volume mount.
        # production-report container usually mounts the app dir.
        # Let's try running it assuming it's mounted or just copy it in.
        
        # Copy to container first to be safe
        print("Copying script into container...")
        client.exec_command(f"cd {REMOTE_DIR} && docker cp test_id_reset_remote.py production-report:/app/test_id_reset_remote.py")
        
        # Run
        print("Executing test inside container...")
        stdin, stdout, stderr = client.exec_command(f"docker exec production-report python /app/test_id_reset_remote.py")
        
        out = stdout.read().decode()
        err = stderr.read().decode()
        print("--- REMOTE OUTPUT ---")
        print(out)
        if err:
            print("--- REMOTE ERROR ---")
            print(err)
            
        # Cleanup
        client.exec_command(f"rm {REMOTE_DIR}/test_id_reset_remote.py")
        client.exec_command(f"docker exec production-report rm /app/test_id_reset_remote.py")

    except Exception as e:
        print(f"Connection Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    run_remote()
