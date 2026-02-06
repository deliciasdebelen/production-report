import paramiko

hostname = "192.168.1.79"
username = "administrador"
password = "GRW7czL3*"
port = 22
base_path = "/home/administrador/sistema_ia_profit"
ssl_conf_path = f"{base_path}/openssl_legacy_debian.cnf"
compose_path = f"{base_path}/docker-compose.yml"

# Debian OpenSSL Config with Unsafe Legacy Support
ssl_conf_content = """openssl_conf = default_conf

[default_conf]
ssl_conf = ssl_sect

[ssl_sect]
system_default = system_default_sect

[system_default_sect]
# Allow absolutely everything including SSLv3 and weak ciphers (RC4, etc)
MinProtocol = SSLv3
CipherString = ALL:@SECLEVEL=0
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
    
    # 1. Create config file
    print(f"Creating {ssl_conf_path}...")
    with sftp.open(ssl_conf_path, 'w') as f:
        f.write(ssl_conf_content)
        
    # 2. Update docker-compose.yml
    print("Reading docker-compose.yml...")
    with sftp.open(compose_path, 'r') as f:
        content = f.read().decode()
        
    lines = content.splitlines()
    new_lines = []
    
    in_service = False
    vol_added = False
    env_added = False
    
    for line in lines:
        if "container_name: ia_musculo" in line:
            in_service = True
            
        # Add Volume
        if in_service and "volumes:" in line:
            new_lines.append(line)
            if not vol_added:
                indent = line[:line.find("volumes:")]
                new_lines.append(f"{indent}  - ./openssl_legacy_debian.cnf:/etc/ssl/openssl.cnf")
                vol_added = True
            continue

        # Add Env Var
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
    # We must ensure we recreate the container with new config
    cmd = f"cd {base_path} && docker-compose up -d"
    run_command(client, cmd)
    
    # Verify linkage
    run_command(client, "docker exec ia_musculo env | grep OPENSSL")
    run_command(client, "docker exec ia_musculo cat /etc/ssl/openssl.cnf | grep SECLEVEL")

    client.close()
except Exception as e:
    print(f"Error: {e}")
