import paramiko
import time

hostname = "192.168.1.79"
username = "administrador"
password = "GRW7czL3*"
port = 22
base_path = "/home/administrador/sistema_ia_profit"
compose_path = f"{base_path}/docker-compose.yml"

def run_command(client, command):
    print(f"\n--- Running: {command} ---")
    stdin, stdout, stderr = client.exec_command(command)
    out = stdout.read().decode()
    err = stderr.read().decode()
    print(out)
    if err:
        print(f"STDERR: {err}")
    return out

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, port=port, username=username, password=password)
    
    sftp = client.open_sftp()
    
    print("Reading docker-compose.yml...")
    with sftp.open(compose_path, 'r') as f:
        content = f.read().decode()
        
    lines = content.splitlines()
    new_lines = []
    
    in_service = False
    
    for line in lines:
        stripped = line.strip()
        
        # Detect service block
        if "container_name: ia_musculo" in line:
            in_service = True
        
        # Remove NODE_OPTIONS inside service
        if in_service and "NODE_OPTIONS" in line:
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
    
    # Wait and Verify
    print("Waiting for startup...")
    time.sleep(10)
    run_command(client, "docker exec ia_musculo n8n --version")
    run_command(client, "docker exec ia_musculo openssl version")

    client.close()
except Exception as e:
    print(f"Error: {e}")
