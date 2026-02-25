import paramiko
import time

hostname = "192.168.1.79"
username = "administrador"
password = "GRW7czL3*"
port = 22
base_path = "/home/administrador/sistema_ia_profit"
ssl_conf_path = f"{base_path}/openssl_1_1.cnf"

# Update to allow SSLv3
ssl_conf_content = """openssl_conf = default_conf

[default_conf]
ssl_conf = ssl_sect

[ssl_sect]
system_default = system_default_sect

[system_default_sect]
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
    
    # 1. Check if SSLv3 is supported by the binary
    print("Checking SSLv3 support...")
    run_command(client, "docker exec ia_musculo openssl ciphers -v | grep SSLv3")
    
    sftp = client.open_sftp()
    
    # 2. Update config
    print(f"Updating {ssl_conf_path} to SSLv3...")
    with sftp.open(ssl_conf_path, 'w') as f:
        f.write(ssl_conf_content)
        
    sftp.close()
    
    # 3. Restart to apply
    cmd = f"cd {base_path} && docker-compose restart ia_musculo"
    run_command(client, cmd)
    
    client.close()
except Exception as e:
    print(f"Error: {e}")
