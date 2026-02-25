import paramiko

hostname = "192.168.1.79"
username = "administrador"
password = "GRW7czL3*"
port = 22

def run_command(client, command):
    print(f"\n--- Running: {command} ---")
    stdin, stdout, stderr = client.exec_command(command)
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print(f"STDERR: {err}")

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, port=port, username=username, password=password)

    # Try to pull debian image
    run_command(client, "docker pull n8nio/n8n:0.236.3-debian")
    
    # Also check if just 'latest-debian' works (though that would be new n8n)
    # run_command(client, "docker pull n8nio/n8n:latest-debian")

    client.close()
except Exception as e:
    print(f"Error: {e}")
