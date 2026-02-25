import paramiko
import time

hostname = "192.168.1.79"
username = "administrador"
password = "GRW7czL3*"
port = 22
base_path = "/home/administrador/sistema_ia_profit"
compose_path = f"{base_path}/docker-compose.yml"
ssl_conf_path = f"{base_path}/custom_openssl.cnf"

ssl_conf_content = """openssl_conf = default_conf

[default_conf]
ssl_conf = ssl_sect

[ssl_sect]
system_default = system_default_sect

[system_default_sect]
MinProtocol = TLSv1.0
CipherString = DEFAULT:@SECLEVEL=0
Options = UnsafeLegacyRenegotiation
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
    
    # 1. Create custom_openssl.cnf
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
    env_added = False
    vol_added = False
    
    # Heuristic parsing
    skip_command = False
    
    for line in lines:
        stripped = line.strip()
        
        # Detect service block
        if "container_name: ia_musculo" in line:
            in_service = True
        elif line.strip() == "" or (in_service and line.startswith("  ") and not line.startswith("    ")):
            # Probably exit service block if indentation changes back? 
            # YAML is hard to parse line-by-line without state. 
            # But the structure is usually:
            # services:
            #   ia_musculo:
            #     ...
            #   other_service:
            # So if we see a line with same indentation as 'ia_musculo:' (which is usually 2 spaces), we are out.
            # 'container_name' is usually indented 4 spaces.
            pass
            
        # 2a. Remove command
        if in_service and "command:" in line:
            # Skip this line
            # If command is multiline (which it was), we need to skip until next key
            # But my previous fix made it single line.
            # Let's assume single line or we check next lines.
            skip_command = True
            continue
            
        # Handle multiline skip if needed (simple check: if next line is indented more than 'command:', skip it?)
        # For now, assuming the command I wrote in previous step is single line or I can just drop lines that start with spaces if I'm in skip mode?
        # Safe bet: If I see a new property key (like volumes:, environment:, etc), stop skipping.
        if skip_command:
            # If line has a key, stop skipping
            if ":" in line and not line.strip().startswith("-"):
                skip_command = False
            else:
                continue
                
        # 2b. Add Env Var
        if in_service and "environment:" in line:
            new_lines.append(line)
            # Add our var immediately
            indent = line[:line.find("environment:")]
            new_lines.append(f"{indent}  - OPENSSL_CONF=/etc/ssl/openssl.cnf")
            env_added = True
            continue
            
        # 2c. Add Volume
        if in_service and "volumes:" in line:
            new_lines.append(line)
            indent = line[:line.find("volumes:")]
            new_lines.append(f"{indent}  - ./custom_openssl.cnf:/etc/ssl/openssl.cnf")
            vol_added = True
            continue

        new_lines.append(line)
        
    final_content = "\n".join(new_lines)

    print("Writing docker-compose.yml...")
    with sftp.open(compose_path, 'w') as f:
        f.write(final_content)
        
    sftp.close()
    
    # 3. Apply changes
    cmd = f"cd {base_path} && docker-compose up -d"
    run_command(client, cmd)
    
    # 4. Verify
    time.sleep(5)
    run_command(client, "docker ps --filter name=ia_musculo")
    run_command(client, "docker exec ia_musculo ping -c 1 carmal_a")

    client.close()
except Exception as e:
    print(f"Error: {e}")
