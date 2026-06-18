import paramiko

hostname = "192.168.1.79"
username = "administrador"
password = "GRW7czL3*"
port = 22
base_path = "/home/administrador/sistema_ia_profit"
compose_path = f"{base_path}/docker-compose.yml"

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
    
    # 1. Check if node is linked to system openssl
    print("Checking Node linkage...")
    run_command(client, "docker exec ia_musculo ldd /usr/local/bin/node")

    sftp = client.open_sftp()
    
    # 2. Add OPENSSL_CONF env var
    print("Reading docker-compose.yml...")
    with sftp.open(compose_path, 'r') as f:
        content = f.read().decode()
        
    lines = content.splitlines()
    new_lines = []
    
    in_service = False
    env_added = False
    
    for line in lines:
        if "container_name: ia_musculo" in line:
            in_service = True
        
        # Add env var if not present
        if in_service and "environment:" in line:
            new_lines.append(line)
            if not env_added:
                indent = line[:line.find("environment:")]
                new_lines.append(f"{indent}  - OPENSSL_CONF=/etc/ssl/openssl.cnf")
                env_added = True
            continue
            
        new_lines.append(line)
        
    final_content = "\n".join(new_lines)
    
    print("Writing docker-compose.yml...")
    with sftp.open(compose_path, 'w') as f:
        f.write(final_content)
        
    sftp.close()
    
    # Apply
    cmd = f"cd {base_path} && docker-compose up -d"
    run_command(client, cmd)
    
    # Verify env
    run_command(client, "docker exec ia_musculo env | grep OPENSSL")

    client.close()
except Exception as e:
    print(f"Error: {e}")
