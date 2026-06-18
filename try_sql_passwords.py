import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22
TARGET_SQL = "192.168.1.205"
SQL_USER = "sa"

def try_sql(client, password):
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{password}" '
        f'-Q "SELECT DB_NAME()" -h -1 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
    out = stdout.read().decode(errors='replace').strip()
    return out

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)
    
    passwords_to_try = [
        "GRW7czL3*",
        "Sistemas1*",
        "Admin123*",
        "carmal123",
        "123456",
        "Carmal2024*",
        "Sistemas123",
        "GRW7czL3",
        "Admin@2024",
        "profit123",
        "Profit123*",
        "carmal@2024",
        "Carmal1*",
        "S1stemas*",
        "deliciasbelen",
        "Belen2024*"
    ]
    
    print(f"Probando {len(passwords_to_try)} contrasenas para sa@{TARGET_SQL}...")
    
    for pwd in passwords_to_try:
        result = try_sql(client, pwd)
        if 'Login failed' not in result and 'Error' not in result:
            print(f"SUCCESS! Password: {pwd}")
            print(f"Result: {result}")
            break
        else:
            print(f"FAIL  [{pwd[:8]}...]: {result[:60]}")
    
    # Also list databases visible
    print("\n=== También probando Windows Auth ===")
    cmd_win = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -E '
        f'-Q "SELECT DB_NAME()" -h -1 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd_win, timeout=15)
    print(stdout.read().decode(errors='replace').strip()[:300])
    
    client.close()

if __name__ == "__main__":
    run()
