import paramiko
import time

hostname = "192.168.1.79"
username = "administrador"
password = "GRW7czL3*"
port = 22
base_path = "/home/administrador/sistema_ia_profit"
ssl_conf_path = f"{base_path}/custom_openssl.cnf"

# A more aggressive OpenSSL 3 config that activates the legacy provider
ssl_conf_content = """openssl_conf = openssl_init

[openssl_init]
providers = provider_sect
ssl_conf = ssl_sect

[provider_sect]
default = default_sect
legacy = legacy_sect

[default_sect]
activate = 1

[legacy_sect]
activate = 1

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
    
    # 1. Update custom_openssl.cnf
    print(f"Updating {ssl_conf_path}...")
    with sftp.open(ssl_conf_path, 'w') as f:
        f.write(ssl_conf_content)
        
    sftp.close()
    
    # 2. Restart container to pick up changes (openssl config interacts with process startup)
    cmd = f"cd {base_path} && docker-compose restart ia_musculo"
    run_command(client, cmd)
    
    # 3. Verify uptime
    time.sleep(5)
    run_command(client, "docker ps --filter name=ia_musculo")

    client.close()
except Exception as e:
    print(f"Error: {e}")
