import paramiko
import sys

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22
REMOTE_DIR = "/home/administrador/apps/production-report"

def check_sqlite_data():
    print(f"Connecting to {HOSTNAME}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
        
        # Check file size first
        stdin, stdout, stderr = client.exec_command(f"ls -l {REMOTE_DIR}/production.db")
        print("File info:", stdout.read().decode())
        
        # Check row counts in SQLite
        # Use single quotes for SQL literals inside the python script
        cmd_str = """
import sqlite3
conn = sqlite3.connect('/app/production.db')
cursor = conn.cursor()
# Use single quotes for SQL string literal 'table'
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [r[0] for r in cursor.fetchall()]
for t in tables:
    try:
        # Use single quotes for f-string to allow double quotes if needed, 
        # but here we just need a string. 
        # Actually, outer shell uses ", so inner python uses '. 
        # But cmd_str is passed in "...", so we escape " as \\".
        # Let's use simple logic:
        count = cursor.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"{t}: {count}")
    except Exception as e:
        print(f"{t}: Error {e}")
"""
        # Escape double quotes for the shell command
        cmd_str_escaped = cmd_str.replace('"', '\\"')
        
        cmd = (
            f"cd {REMOTE_DIR} && "
            f"docker-compose run --rm web python -c \"{cmd_str_escaped}\""
        )
        
        print(f"Executing: {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd)
        
        print(stdout.read().decode())
        err = stderr.read().decode()
        if err:
            print("STDERR:", err)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    check_sqlite_data()
