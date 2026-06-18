import paramiko

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
    
    query = "ALTER TABLE support_settings ADD COLUMN IF NOT EXISTS cc_emails VARCHAR DEFAULT '';"
    cmd = f'echo "{PASSWORD}" | sudo -S docker exec production-report-db psql -U app_user -d production_db -c "{query}"'
    
    stdin, stdout, stderr = client.exec_command(cmd)
    
    print("STDOUT:")
    print(stdout.read().decode())
    print("STDERR:")
    print(stderr.read().decode())
    
    client.close()

if __name__ == "__main__":
    run()
