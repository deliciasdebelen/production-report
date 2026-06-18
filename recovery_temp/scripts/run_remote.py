import paramiko
import sys

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"

def run_remote_cmd(cmd):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOSTNAME, port=22, username=USERNAME, password=PASSWORD)
        
        stdin, stdout, stderr = client.exec_command(cmd)
        content = stdout.read().decode()
        error = stderr.read().decode()
        
        client.close()
        return content, error
    except Exception as e:
        return None, str(e)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_remote.py \"command\"")
        sys.exit(1)
    
    cmd = sys.argv[1]
    content, error = run_remote_cmd(cmd)
    if content:
        print(content)
    if error:
        print(f"Error: {error}")
