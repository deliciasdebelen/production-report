import paramiko

hostname = "192.168.1.79"
username = "administrador"
password = "GRW7czL3*"
port = 22
base_path = "/home/administrador/sistema_ia_profit"
ssl_conf_path = f"{base_path}/openssl_1_1.cnf"
compose_path = f"{base_path}/docker-compose.yml"

# OpenSSL 1.1 Config for Legacy Support
ssl_conf_content = """openssl_conf = default_conf

[default_conf]
ssl_conf = ssl_sect

[ssl_sect]
system_default = system_default_sect

[system_default_sect]
MinProtocol = TLSv1.0
CipherString = DEFAULT@SECLEVEL=0
"""

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
    
    # 1. Create config
    print(f"Creating {ssl_conf_path}...")
    with sftp.open(ssl_conf_path, 'w') as f:
        f.write(ssl_conf_content)
        
    # 2. Update docker-compose.yml to mount it
    print("Reading docker-compose.yml...")
    with sftp.open(compose_path, 'r') as f:
        content = f.read().decode()
        
    lines = content.splitlines()
    new_lines = []
    
    in_service = False
    vol_exist = False
    env_exist = False
    
    for line in lines:
        if "container_name: ia_musculo" in line:
            in_service = True
            
        # Re-add volumes if I removed them?
        # My previous script removed them.
        # So I need to add them again.
        
        if in_service and "volumes:" in line:
            new_lines.append(line)
            indent = line[:line.find("volumes:")]
            # Mount to /etc/ssl/openssl.cnf
            new_lines.append(f"{indent}  - ./openssl_1_1.cnf:/etc/ssl/openssl.cnf")
            vol_exist = True
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
    
    # Verify
    run_command(client, "docker exec ia_musculo grep SECLEVEL /etc/ssl/openssl.cnf")

    client.close()
except Exception as e:
    print(f"Error: {e}")
