import paramiko
import os

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22

def fix_permissions_and_deploy():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("Connecting to server...")
    client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
    
    print("Fixing folder permissions...")
    # Use echo password | sudo -S to execute sudo command without interactive prompt
    cmds = [
        f"echo '{PASSWORD}' | sudo -S chown -R {USERNAME}:{USERNAME} /home/{USERNAME}/apps/production-report",
        f"echo '{PASSWORD}' | sudo -S chmod -R 775 /home/{USERNAME}/apps/production-report"
    ]
    
    for cmd in cmds:
        stdin, stdout, stderr = client.exec_command(cmd)
        print(stdout.read().decode())
        err = stderr.read().decode()
        if err:
             print(f"Error: {err}")
             
    client.close()
    
    print("Permissions fixed. Redeploying...")
    # Now run the deploy_prod_v3.py script locally
    os.system("python deploy_prod_v3.py")

if __name__ == "__main__":
    fix_permissions_and_deploy()
