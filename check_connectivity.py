import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22

TARGET_SQL = "192.168.1.205"

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)

    # 1. Check nc/ping to 205
    print("=== PING A 192.168.1.205 ===")
    stdin, stdout, stderr = client.exec_command("ping -c 3 192.168.1.205")
    print(stdout.read().decode(errors='replace').strip())
    
    # 2. Find sqlcmd on the system
    print("\n=== BUSCANDO sqlcmd en el servidor 79 ===")
    stdin, stdout, stderr = client.exec_command("which sqlcmd 2>/dev/null || find /usr -name sqlcmd 2>/dev/null || find /opt -name sqlcmd 2>/dev/null")
    out = stdout.read().decode(errors='replace').strip()
    print(out or "(sqlcmd no encontrado)")
    
    # 3. Check if port 1433 on 205 is reachable
    print("\n=== VERIFICANDO PUERTO 1433 en 205 ===")
    stdin, stdout, stderr = client.exec_command(f"nc -z -w 3 {TARGET_SQL} 1433 && echo 'PUERTO ABIERTO' || echo 'PUERTO CERRADO'")
    print(stdout.read().decode(errors='replace').strip())
    
    # 4. List docker containers
    print("\n=== CONTENEDORES DOCKER ACTIVOS ===")
    stdin, stdout, stderr = client.exec_command(f'echo "{JUMP_PASS}" | sudo -S docker ps --format "{{{{.Names}}}}\\t{{{{.Image}}}}\\t{{{{.Status}}}}"')
    print(stdout.read().decode(errors='replace').strip())
    
    client.close()

if __name__ == "__main__":
    run()
