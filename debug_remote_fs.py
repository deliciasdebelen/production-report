import paramiko

hostname = "192.168.1.79"
username = "administrador"
password = "GRW7czL3*"
port = 22
remote_dir = "/home/administrador/apps/production-report"

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, port, username, password)
    
    print("--- Listing Home ---")
    stdin, stdout, stderr = client.exec_command("ls -la /home/administrador")
    print(stdout.read().decode())

    print(f"--- Listing {remote_dir} ---")
    stdin, stdout, stderr = client.exec_command(f"ls -la {remote_dir}")
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    client.close()

except Exception as e:
    print(f"Error: {e}")
