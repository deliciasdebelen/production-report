import paramiko

hostname = "192.168.1.79"
username = "administrador"
password = "GRW7czL3*"
port = 22
remote_path = "/home/administrador/apps/production-report/docker-compose.yml"

try:
    transport = paramiko.Transport((hostname, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    
    print(f"Reading {remote_path}...")
    with sftp.open(remote_path, 'r') as f:
        print(f.read().decode())
        
    sftp.close()
    transport.close()

except Exception as e:
    print(f"Error: {e}")
