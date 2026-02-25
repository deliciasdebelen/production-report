
import paramiko

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22

def fetch_logs():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOSTNAME, port=PORT, username=USERNAME, password=PASSWORD)
        
        # Fetch last 50 lines of logs
        cmd = "docker logs --tail 50 production-report"
        stdin, stdout, stderr = client.exec_command(cmd)
        
        print("--- LOGS ---")
        print(stdout.read().decode())
        print("--- STDERR ---")
        print(stderr.read().decode())

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    fetch_logs()
