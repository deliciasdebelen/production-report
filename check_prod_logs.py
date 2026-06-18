import paramiko

# Configuration
HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22
REMOTE_DIR = "/home/administrador/apps/production-report"

def check_logs():
    try:
        print(f"Connecting to {HOSTNAME}...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
        
        cmd = f"cd {REMOTE_DIR} && docker-compose logs --tail=100 web"
        print(f"Executing: {cmd}")
        
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode()
        err = stderr.read().decode()
        
        print("--- LOGS START ---")
        print(out)
        print("--- LOGS END ---")
        
        if err:
            print("--- STDERR ---")
            print(err)
            
        client.close()
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    check_logs()
