import paramiko

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
    
    # Run a temporary container from production-report-web
    cmd = 'echo "GRW7czL3*" | sudo -S docker run --rm production-report-web cat /app/app/main.py'
    stdin, stdout, stderr = client.exec_command(cmd)
    
    with open("../Projects/production-report/original_main.py", "w") as f:
        f.write(stdout.read().decode())
        
    client.close()

if __name__ == "__main__":
    run()
