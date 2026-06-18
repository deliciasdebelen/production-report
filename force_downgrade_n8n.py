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
        
    print("-- Current Content Snippet --")
    idx = content.find("image: n8nio/n8n")
    print(content[idx:idx+50])
    
    # Simple string replace is safer if the file is consistent
    if "image: n8nio/n8n:latest" in content:
        new_content = content.replace("image: n8nio/n8n:latest", "image: n8nio/n8n:0.236.3")
    else:
        # Maybe it has a comment or something?
        # Let's use lines again but be careful
        lines = content.splitlines()
        new_lines = []
        for line in lines:
            if "image: n8nio/n8n" in line:
                # Keep indentation
                indent = line.split("image:")[0]
                new_lines.append(f"{indent}image: n8nio/n8n:0.236.3")
            elif "OPENSSL_CONF" in line or "custom_openssl.cnf" in line:
                # Remove these as planned
                continue
            else:
                new_lines.append(line)
        new_content = "\n".join(new_lines)
        
    print("Writing docker-compose.yml...")
    with sftp.open(compose_path, 'w') as f:
        f.write(new_content)
        
    sftp.close()
    
    # Verify file content
    run_command(client, f"cat {compose_path} | grep 'image: n8nio/n8n'")
    
    # Apply
    # Pull first to ensure it exists
    # run_command(client, "docker pull n8nio/n8n:0.236.3") # Optional, compose does it
    
    cmd = f"cd {base_path} && docker-compose up -d"
    run_command(client, cmd)
    
    # Wait and Verify
    print("Waiting for startup...")
    time.sleep(15)
    run_command(client, "docker exec ia_musculo n8n --version")
    run_command(client, "docker exec ia_musculo openssl version")

    client.close()
except Exception as e:
    print(f"Error: {e}")
