import paramiko

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
    
    cmd = 'echo "GRW7czL3*" | sudo -S docker logs --tail 50 production-report'
    stdin, stdout, stderr = client.exec_command(cmd)
    
    print("STDOUT:")
    print(stdout.read().decode())
    print("STDERR:")
    print(stderr.read().decode())
    
    client.close()

if __name__ == "__main__":
    run()
