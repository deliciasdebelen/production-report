import paramiko
import time

hostname = "192.168.1.79"
username = "administrador"
password = "GRW7czL3*"
port = 22
remote_path = "/home/administrador/sistema_ia_profit/docker-compose.yml"

new_config = """    extra_hosts:
      - "carmal_a:192.168.1.205"
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
    
    # 1. Read existing file
    print("Reading remote file...")
    with sftp.open(remote_path, 'r') as f:
        content = f.read().decode()
    
    # 2. Modify content
    if "carmal_a:192.168.1.205" in content:
        print("Configuration already present. Skipping file edit.")
    else:
        # Find 'container_name: ia_musculo' and find a suitable place to insert
        # We'll insert before 'volumes:' inside that service block
        lines = content.splitlines()
        new_lines = []
        in_service = False
        inserted = False
        
        for line in lines:
            if "container_name: ia_musculo" in line:
                in_service = True
            
            # Simple heuristic: insert before 'volumes:' if we are in the service and haven't inserted yet
            if in_service and "volumes:" in line and not inserted:
                # Detect indentation of the 'volumes:' line to match
                indent = line[:line.find("volumes:")]
                new_lines.append(f"{indent}{new_config.strip()}")
                new_lines.append(f"{indent}  - {new_config.splitlines()[1].strip()[2:]}") # Dirty hack? No, let's just use the string block
                # Actually, let's just insert the string verbatim but indented correctly
                # My new_config string has 4 spaces. The file seems to use 2 or 4.
                # Let's inspect indentation of 'volumes:'
                new_lines.append(f"{indent}extra_hosts:")
                new_lines.append(f"{indent}  - \"carmal_a:192.168.1.205\"")
                inserted = True
                in_service = False # Reset so we don't insert again
            
            new_lines.append(line)
            
        final_content = "\n".join(new_lines)
        
        # 3. Write back
        print("Writing modified file...")
        with sftp.open(remote_path, 'w') as f:
            f.write(final_content)
            
    sftp.close()

    # 4. Restart Docker Compose
    cmd = "cd /home/administrador/sistema_ia_profit && docker-compose up -d"
    run_command(client, cmd)

    # 5. Verify connectivity from inside container
    print("Verifying fix...")
    # Give it a moment to restart if needed
    time.sleep(5)
    run_command(client, "docker exec ia_musculo ping -c 2 carmal_a")

    client.close()
except Exception as e:
    print(f"Error: {e}")
