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

    # Search for the compose file that defines 'ia_musculo' or just search for yml files in typical dirs
    # Check parent directory or other folders
    run_command(client, "find /home/administrador -name 'docker-compose.y*ml' -maxdepth 3")
    
    # Also grep for the container name in files to be sure
    run_command(client, "grep -r 'container_name: ia_musculo' /home/administrador")

    client.close()
except Exception as e:
    print(f"Error: {e}")
