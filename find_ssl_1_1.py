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

    # 1. Identify OS and OpenSSL config location
    print("Checking OS release...")
    run_command(client, "docker exec ia_musculo cat /etc/os-release")
    
    print("Finding openssl.cnf...")
    # Common locations
    run_command(client, "docker exec ia_musculo ls /etc/ssl/openssl.cnf")
    run_command(client, "docker exec ia_musculo ls /usr/lib/ssl/openssl.cnf")
    
    # 2. Check defaults
    print("Checking default config...")
    # This might fail if openssl command isn't in path (user saw that error earlier), 
    # but 0.236.3 is likely Alpine-based and has it.
    # The error "executable file not found in $PATH" earlier suggested the previous image didn't have it? 
    # Or maybe the path was weird. 
    # Let's try `apk info` or similar if it's alpine.

    client.close()
except Exception as e:
    print(f"Error: {e}")
