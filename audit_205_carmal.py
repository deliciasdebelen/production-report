import paramiko

HOST_79 = "192.168.1.79"
USER    = "administrador"
PASS    = "GRW7czL3*"

def ssh(cmd, host=HOST_79, timeout=25):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, 22, USER, PASS, timeout=10)
    _, out, err = c.exec_command(cmd, timeout=timeout)
    r = out.read().decode("utf-8", errors="replace").strip()
    e = err.read().decode("utf-8", errors="replace").strip()
    c.close()
    return r or e

SUDO = f'echo "{PASS}" | sudo -S'

print("=" * 60)
print("AUDITORIA IA INTERNA + n8n + CARMAL_A")
print("=" * 60)

# 1. Todos los contenedores en .79
print("\n[1] TODOS los contenedores en .79:")
print(ssh(f'{SUDO} docker ps -a --format "{{{{.Names}}}}\\t{{{{.Image}}}}\\t{{{{.Status}}}}" 2>&1'))

# 2. Buscar carmal en toda la app
print("\n[2] Referencias a 'carmal' en el codigo de la app:")
print(ssh(f'grep -rn "carmal" /home/administrador/apps/ 2>&1 | head -30'))

# 3. Buscar n8n y 205 en toda la infra
print("\n[3] Referencias a n8n en el servidor:")
print(ssh(f'grep -rn "n8n\\|205\\." /home/administrador/apps/ 2>&1 | grep -v ".pyc" | head -30'))

# 4. Buscar OpenWebUI/Ollama/OpenClaw
print("\n[4] Servicios AI (ollama, openwebui, openclaw, openai):")
print(ssh(f'{SUDO} docker ps -a 2>&1 | grep -iE "ollama|webui|openclaw|openai|n8n|ai"'))

# 5. Variables de entorno completas de la app
print("\n[5] ENV completo del contenedor production-report:")
print(ssh(f'{SUDO} docker exec production-report env 2>&1 | sort'))

# 6. docker-compose completo
print("\n[6] docker-compose.yml en .79:")
print(ssh(f'cat /home/administrador/apps/production-report/docker-compose.yml 2>&1'))

# 7. Buscar scripts/workers que hacen queries a bases externas
print("\n[7] Workers/scripts con conexion a BD externa:")
print(ssh(f'find /home/administrador/apps -name "*.py" 2>/dev/null | xargs grep -l "carmal\\|205\\|SQLSRV\\|profit\\|ProPlus" 2>/dev/null | head -20'))

# 8. Connectivity test to 205
print("\n[8] Ping/nc desde .79 a 192.168.1.205:")
print(ssh(f'ping -c 2 192.168.1.205 2>&1 | tail -3'))
print(ssh(f'nc -z -w 3 192.168.1.205 22 2>&1 && echo "SSH:OPEN" || echo "SSH:CLOSED"'))
print(ssh(f'nc -z -w 3 192.168.1.205 5432 2>&1 && echo "PG:OPEN" || echo "PG:CLOSED"'))
print(ssh(f'nc -z -w 3 192.168.1.205 1433 2>&1 && echo "MSSQL:OPEN" || echo "MSSQL:CLOSED"'))
