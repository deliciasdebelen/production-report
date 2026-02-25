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

    # Check Node's internal OpenSSL version
    run_command(client, 'docker exec ia_musculo node -p "process.versions.openssl"')
    
    # Check OS version again
    run_command(client, "docker exec ia_musculo cat /etc/os-release")

    client.close()
except Exception as e:
    print(f"Error: {e}")
