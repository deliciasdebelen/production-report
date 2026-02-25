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
        elif line.strip() == "" or (in_service and line.startswith("  ") and not line.startswith("    ")):
            pass # heuristics
            
        # 1. Change Image
        if in_service and "image:" in line and "n8n" in line:
            indent = line[:line.find("image:")]
            new_lines.append(f"{indent}image: n8nio/n8n:0.236.3")
            continue
            
        # 2. Remove OpenSSL Environment Variable
        if in_service and "OPENSSL_CONF" in line:
            continue
            
        # 3. Remove OpenSSL Volume
        if in_service and "custom_openssl.cnf" in line:
            continue
            
        new_lines.append(line)
        
    final_content = "\n".join(new_lines)
    
    print("Writing docker-compose.yml...")
    with sftp.open(compose_path, 'w') as f:
        f.write(final_content)
        
    sftp.close()
    
    # 4. Apply changes (Recreate container)
    cmd = f"cd {base_path} && docker-compose up -d"
    run_command(client, cmd)
    
    # 5. Verify Version
    print("Verifying version...")
    time.sleep(10) # Give it time to download image and start
    run_command(client, "docker exec ia_musculo n8n --version")
    
    # 6. Verify Ping just in case
    run_command(client, "docker exec ia_musculo ping -c 1 carmal_a")

    client.close()
except Exception as e:
    print(f"Error: {e}")
