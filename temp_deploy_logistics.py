import paramiko
import os

def deploy():
    host = "192.168.1.79"
    user = "administrador"
    pw = "GRW7czL3*"
    
    local_path = r"c:\Users\ovargas\Projects\production-report\app\routers\logistics.py"
    remote_path = "/home/administrador/apps/production-report/app/routers/logistics.py"
    
    local_tpl = r"c:\Users\ovargas\Projects\production-report\app\templates\logistics\invoice_dispatch.html"
    remote_tpl = "/home/administrador/apps/production-report/app/templates/logistics/invoice_dispatch.html"
    
    print(f"Connecting to {host}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, password=pw)
    
    print(f"Uploading files...")
    sftp = client.open_sftp()
    sftp.put(local_path, remote_path)
    sftp.put(local_tpl, remote_tpl)
    sftp.close()
    
    print("Restarting container...")
    stdin, stdout, stderr = client.exec_command("docker restart production-report")
    print(stdout.read().decode())
    
    client.close()
    print("Deployment finished.")

if __name__ == "__main__":
    deploy()
