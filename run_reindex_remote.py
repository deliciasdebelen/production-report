
import paramiko

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"

def main():
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOSTNAME, 22, USERNAME, PASSWORD)
        
        # Execute inside container
        # Note: path is /app/app/reindex_db.py because we mount ./app:/app/app mostly?
        # Let's check where it lands. Usually ./app maps to /app/app.
        # But wait, deploy structure: 
        # app/ is inside root. 
        # Dockerfile Workdir /app. 
        # COPY . /app
        # So it should be at /app/app/reindex_db.py
        
        cmd = "docker exec production-report python /app/app/migrate_db.py"
        print(f"Executing: {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd)
        
        print("--- OUTPUT ---")
        print(stdout.read().decode())
        print("--- ERROR ---")
        print(stderr.read().decode())
        
        client.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
