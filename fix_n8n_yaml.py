import paramiko
import re

hostname = "192.168.1.79"
username = "administrador"
password = "GRW7czL3*"
port = 22
remote_path = "/home/administrador/sistema_ia_profit/docker-compose.yml"

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
    
    sftp = client.open_sftp()
    
    print("Reading remote file...")
    with sftp.open(remote_path, 'r') as f:
        content = f.read().decode()
    
    # Simple state machine to clean up
    lines = content.splitlines()
    new_lines = []
    
    # We want to remove all 'extra_hosts' and lines starting with '- "carmal_a' inside ia_musculo service
    # And then insert it properly once.
    
    skip_mode = False
    
    for line in lines:
        stripped = line.strip()
        
        # Detect if we are looking at the bad blocks
        if "extra_hosts:" in line:
            # Skip this line
            continue
        if "carmal_a:192.168.1.205" in line:
            # Skip this line
            continue
            
        new_lines.append(line)

    # Now we have the file WITHOUT carmal_a. Let's insert it correctly.
    final_lines = []
    inserted = False
    in_service = False
    
    for line in new_lines:
        if "container_name: ia_musculo" in line:
            in_service = True
        
        if in_service and "volumes:" in line and not inserted:
            # Insert here
            indent = line[:line.find("volumes:")]
            final_lines.append(f"{indent}extra_hosts:")
            final_lines.append(f"{indent}  - \"carmal_a:192.168.1.205\"")
            inserted = True
            in_service = False
            
        final_lines.append(line)
        
    final_content = "\n".join(final_lines)
    
    print("Writing fixed file...")
    with sftp.open(remote_path, 'w') as f:
        f.write(final_content)
            
    sftp.close()

    # Restart
    cmd = "cd /home/administrador/sistema_ia_profit && docker-compose up -d"
    run_command(client, cmd)
    
    # Verify
    print("Verifying fix...")
    run_command(client, "docker exec ia_musculo ping -c 1 carmal_a")

    client.close()
except Exception as e:
    print(f"Error: {e}")
