import paramiko

# Configuration
HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22
REMOTE_DIR = "/home/administrador/apps/production-report"

def fix_schema():
    print(f"Connecting to {HOSTNAME}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
        
        # Commands to run inside container
        cmds = [
            # Check if columns exist via migration script
            f"cd {REMOTE_DIR} && docker-compose exec -T web python -m app.migrate_db",
            # Also notifications table if missing
            f"cd {REMOTE_DIR} && docker-compose exec -T web python -m app.migrate_notifications"
        ]
        
        for cmd in cmds:
            print(f"Executing: {cmd}")
            stdin, stdout, stderr = client.exec_command(cmd)
            out = stdout.read().decode()
            err = stderr.read().decode()
            
            if out: print("STDOUT:", out)
            if err: print("STDERR:", err)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    fix_schema()
