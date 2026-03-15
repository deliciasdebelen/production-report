import paramiko
import os

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
REMOTE_PATH = "/tmp/production_db_restore.sql"
LOCAL_FILE = "production_db_portable.sql"

def restore_db():
    try:
        print(f"Uploading {LOCAL_FILE} to {HOSTNAME}...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOSTNAME, port=22, username=USERNAME, password=PASSWORD)
        
        sftp = client.open_sftp()
        sftp.put(LOCAL_FILE, REMOTE_PATH)
        sftp.close()
        
        print("Restoring database inside the container...")
        # 1. Drop and recreate DB inside PG container (clean start)
        # We'll use psql to drop/create
        cmd_recreate = (
            "docker exec production-report-db psql -U app_user -d production_db -c "
            "\"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'production_db' AND pid <> pg_backend_pid();\" && "
            "docker exec production-report-db dropdb -U app_user production_db || true && "
            "docker exec production-report-db createdb -U app_user production_db"
        )
        stdin, stdout, stderr = client.exec_command(cmd_recreate)
        print(stdout.read().decode())
        print(stderr.read().decode())
        
        # 2. Restore from SQL file
        # We need to cat the file to docker exec -i
        cmd_restore = f"cat {REMOTE_PATH} | docker exec -i production-report-db psql -U app_user -d production_db"
        print(f"Executing: {cmd_restore}")
        stdin, stdout, stderr = client.exec_command(cmd_restore)
        print(stdout.read().decode())
        print(stderr.read().decode())
        
        # Cleanup
        client.exec_command(f"rm {REMOTE_PATH}")
        client.close()
        print("Database restored successfully.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    restore_db()
