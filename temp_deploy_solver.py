import paramiko
import os

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22
REMOTE_SERVICES_DIR = "/home/administrador/apps/production-report/app/services"

def deploy_solver_update():
    try:
        print(f"Conectando a {HOSTNAME}...")
        transport = paramiko.Transport((HOSTNAME, PORT))
        transport.connect(username=USERNAME, password=PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        local_path = "app/services/stock_solver.py"
        remote_name = "stock_solver.py"
        
        if os.path.exists(local_path):
            print(f"Subiendo {local_path}...")
            # Note: We upload to the remote app dir which is mapped in docker-compose
            sftp.put(local_path, f"{REMOTE_SERVICES_DIR}/{remote_name}")
        else:
            print("❌ Archivo local no encontrado")
            return
            
        sftp.close()
        transport.close()
        
        print("Reiniciando contenedor web...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
        
        cmd = "cd ~/apps/production-report && docker-compose restart web"
        stdin, stdout, stderr = client.exec_command(cmd)
        print(stdout.read().decode())
        
        client.close()
        print("✅ Motor de auditoría IA Belén actualizado con éxito.")
        
    except Exception as e:
        print(f"❌ Error en el despliegue: {e}")

if __name__ == "__main__":
    deploy_solver_update()
