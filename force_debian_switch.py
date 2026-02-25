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
        
    # Direct replacement
    if "n8nio/n8n:0.236.3-debian" in content:
        print("Already updated?")
    else:
        new_content = content.replace("n8nio/n8n:0.236.3", "n8nio/n8n:0.236.3-debian")
        
        # Also clean up OPENSSL_CONF just in case logic failed before
        # Using a simple line filtering
        lines = new_content.splitlines()
        final_lines = [l for l in lines if "OPENSSL_CONF" not in l]
        # Also remove openssl volumes
        final_lines = [l for l in final_lines if "openssl.cnf" not in l]
        
        final_content = "\n".join(final_lines)
        
        print("Writing docker-compose.yml...")
        with sftp.open(compose_path, 'w') as f:
            f.write(final_content)
    
    sftp.close()
    
    # Apply
    cmd = f"cd {base_path} && docker-compose up -d"
    run_command(client, cmd)
    
    # Limit wait time
    print("Waiting for startup (10s)...")
    time.sleep(10)
    
    # Verify OS
    run_command(client, "docker exec ia_musculo cat /etc/os-release")

    client.close()
except Exception as e:
    print(f"Error: {e}")
