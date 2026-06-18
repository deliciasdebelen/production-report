import paramiko
import sys

# Configuration
HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22
REMOTE_DIR = "/home/administrador/apps/production-report"

def check_remote_counts():
    print(f"Connecting to {HOSTNAME}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
        
        # Python script to check counts
        cmd_str = """
from sqlalchemy import create_engine, inspect, text
e = create_engine("postgresql://app_user:production_password@db:5432/production_db")
insp = inspect(e)
tables = insp.get_table_names()
with e.connect() as conn:
    for t in tables:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        print(f"{t}: {count}")
"""
        # Escape for shell
        cmd_str = cmd_str.replace('"', '\\"') 
        
        cmd = (
            f"cd {REMOTE_DIR} && "
            f"docker-compose run --rm web python -c \"{cmd_str}\""
        )
        
        print(f"Executing: {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd)
        
        print(stdout.read().decode())
        print("STDERR:", stderr.read().decode())
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    check_remote_counts()
