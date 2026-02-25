import paramiko

hostname = "192.168.1.79"
username = "administrador"
password = "GRW7czL3*"
port = 22

remote_path = "/home/administrador/sistema_ia_profit/docker-compose.yml"

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, port=port, username=username, password=password)
    
    sftp = client.open_sftp()
    with sftp.open(remote_path, 'r') as f:
        print(f.read().decode())
        
    sftp.close()
    client.close()
except Exception as e:
    print(f"Error: {e}")
