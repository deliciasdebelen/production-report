import paramiko

hostname = "192.168.1.79"
username = "administrador"
password = "GRW7czL3*"
port = 22

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
    
    # 1. Check if openssl is installed in the container
    print("Checking openssl version...")
    run_command(client, "docker exec ia_musculo openssl version")
    
    # 2. Try to connect with s_client to see handshake
    # Note: SQL Server might not return standard HTTP-like handshake immediately on 1433 without STARTTLS equivalent,
    # but usually s_client can see the hello.
    # Actually, SQL Server on 1433 expects TDS packet first, so s_client might hang or fail.
    # But let's try.
    print("Attempting to probe SQL Server SSL...")
    run_command(client, "docker exec ia_musculo openssl s_client -connect 192.168.1.205:1433 -brief")
    
    # 3. Try forcing tls1
    # run_command(client, "docker exec ia_musculo openssl s_client -connect 192.168.1.205:1433 -tls1")

    client.close()
except Exception as e:
    print(f"Error: {e}")
