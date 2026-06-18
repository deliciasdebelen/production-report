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
    
    # 1. Update docker-compose.yml
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
        elif line.strip() == "" or (in_service and line.startswith("  ") and not line.startswith("    ")):
            pass
            
        # 1. Change Image to Debian
        if in_service and "image:" in line and "n8n" in line:
            indent = line[:line.find("image:")]
            new_lines.append(f"{indent}image: n8nio/n8n:0.236.3-debian")
            continue
            
        # 2. Clean up OPENSSL_CONF env var
        if in_service and "OPENSSL_CONF" in line:
            continue
            
        # 3. Clean up openssl volume mounts (both versions I tried)
        if in_service and ("openssl_1_1.cnf" in line or "custom_openssl.cnf" in line):
            continue
            
        new_lines.append(line)
        
    final_content = "\n".join(new_lines)
    
    print("Writing docker-compose.yml...")
    with sftp.open(compose_path, 'w') as f:
        f.write(final_content)
        
    sftp.close()
    
    # 2. Apply changes
    cmd = f"cd {base_path} && docker-compose up -d"
    run_command(client, cmd)
    
    # 3. Verify
    print("Waiting for startup...")
    time.sleep(15) # Pull might take a bit
    
    print("Checking OS version (expecting Debian)...")
    run_command(client, "docker exec ia_musculo cat /etc/os-release")
    
    print("Checking n8n version...")
    run_command(client, "docker exec ia_musculo n8n --version")

    client.close()
except Exception as e:
    print(f"Error: {e}")
