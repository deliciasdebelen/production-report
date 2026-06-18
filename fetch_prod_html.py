import paramiko

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
    
    cmd = 'echo "GRW7czL3*" | sudo -S docker exec production-report cat /app/app/templates/support/management.html'
    stdin, stdout, stderr = client.exec_command(cmd)
    
    html = stdout.read().decode()
    with open("../Projects/production-report/prod_management.html", "w") as f:
        f.write(html)
        
    print("Downloaded to prod_management.html")
    client.close()

if __name__ == "__main__":
    run()
