import paramiko
import os
import tarfile
import shutil
from datetime import datetime
import subprocess

# Remote Configuration
HOST = "192.168.1.79"
USER = "administrador"
PWD = "GRW7czL3*"
REMOTE_APP_DIR = "/home/administrador/apps/production-report"
REMOTE_DUMP_PATH = "/tmp/production_db_sync.sql"
REMOTE_TAR_PATH = "/tmp/app_sync.tar.gz"

# Local Configuration
LOCAL_PG_BIN = r"C:\Program Files\Odoo 18.0.20250508\PostgreSQL\bin"
LOCAL_DB_USER = "openpg"
LOCAL_DB_PWD = "openpgpwd"
LOCAL_DB_NAME = "production_db"

def run_local(cmd, env=None):
    print(f"Executing local: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    return result.stdout, result.returncode

def main():
    print(f"--- Starting Sync from Production ({HOST}) ---")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(HOST, username=USER, password=PWD)
        
        # 1. Archive remote code
        print("1. Archiving remote app code...")
        cmd_tar = f"tar -czf {REMOTE_TAR_PATH} -C {REMOTE_APP_DIR} app requirements.txt Dockerfile docker-compose.yml"
        ssh.exec_command(cmd_tar)
        # Wait for completion (simple way)
        ssh.exec_command(f"ls {REMOTE_TAR_PATH}") 
        
        # 2. Dump remote database from container
        print("2. Dumping remote PostgreSQL database...")
        # We use docker exec to run pg_dump inside the container
        cmd_dump = f"docker exec production-report-db pg_dump -U app_user production_db > {REMOTE_DUMP_PATH}"
        stdin, stdout, stderr = ssh.exec_command(cmd_dump)
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            print(f"Error dumping DB: {stderr.read().decode()}")
            return

        # 3. Download files
        print("3. Downloading files...")
        sftp = ssh.open_sftp()
        sftp.get(REMOTE_TAR_PATH, "app_sync.tar.gz")
        sftp.get(REMOTE_DUMP_PATH, "production_db.sql")
        
        # Cleanup remote
        sftp.remove(REMOTE_TAR_PATH)
        sftp.remove(REMOTE_DUMP_PATH)
        sftp.close()
        ssh.close()
        
    except Exception as e:
        print(f"SSH Error: {e}")
        return

    # 4. Local Backup
    print("4. Backing up local app...")
    if os.path.exists("app"):
        backup_dir = f"app_backup_{timestamp}"
        shutil.copytree("app", backup_dir)
        print(f"Backup created: {backup_dir}")
        shutil.rmtree("app")

    # 5. Extract code
    print("5. Extracting production code...")
    with tarfile.open("app_sync.tar.gz", "r:gz") as tar:
        tar.extractall()
    os.remove("app_sync.tar.gz")

    # 6. Restore Database
    print("6. Restoring local database...")
    # Set PGPASSWORD env var for psql
    env = os.environ.copy()
    env["PGPASSWORD"] = LOCAL_DB_PWD
    
    psql = os.path.join(LOCAL_PG_BIN, "psql.exe")
    createdb = os.path.join(LOCAL_PG_BIN, "createdb.exe")
    dropdb = os.path.join(LOCAL_PG_BIN, "dropdb.exe")
    
    # Drop and recreate DB (clean slate)
    print("Terminating existing connections...")
    term_cmd = f'"{psql}" -U {LOCAL_DB_USER} -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = \'{LOCAL_DB_NAME}\' AND pid <> pg_backend_pid();"'
    run_local(term_cmd, env)
    
    print(f"Dropping local DB {LOCAL_DB_NAME}...")
    run_local(f'"{dropdb}" -U {LOCAL_DB_USER} {LOCAL_DB_NAME}', env)
    
    print(f"Creating local DB {LOCAL_DB_NAME}...")
    run_local(f'"{createdb}" -U {LOCAL_DB_USER} {LOCAL_DB_NAME}', env)
    
    print("Restoring dump...")
    restore_cmd = f'"{psql}" -U {LOCAL_DB_USER} -d {LOCAL_DB_NAME} -f production_db.sql'
    run_local(restore_cmd, env)
    
    # Cleanup local dump
    if os.path.exists("production_db.sql"):
        os.remove("production_db.sql")

    # 7. Update .env
    print("7. Updating .env...")
    env_content = f"DATABASE_URL=postgresql://{LOCAL_DB_USER}:{LOCAL_DB_PWD}@localhost:5432/{LOCAL_DB_NAME}\n"
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("\n--- Sync Completed Successfully ---")

if __name__ == "__main__":
    main()
