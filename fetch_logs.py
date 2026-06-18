import paramiko

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22

def fetch_logs():
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
        
        # Get logs from container (web service in docker-compose)
        # Assuming container name prefix based on folder
        cmd = "cd /home/administrador/apps/production-report && docker-compose logs --tail=50 web"
        
        print(f"Executing: {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd)
        
        out = stdout.read().decode()
        err = stderr.read().decode()
        
        print("--- STDOUT ---")
        print(out)
        print("--- STDERR ---")
        print(err)
        
        client.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_logs()
