import paramiko
import os

HOSTNAME = "192.168.1.193"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22

def prepare_env_and_deploy():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("Connecting to server...")
    try:
        client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
    except Exception as e:
        print(f"Failed to connect to {HOSTNAME}: {e}")
        return

    print("Checking and creating target directory if needed...")
    cmds = [
        f"mkdir -p /home/{USERNAME}/apps/production-report",
        f"echo '{PASSWORD}' | sudo -S chown -R {USERNAME}:{USERNAME} /home/{USERNAME}/apps/production-report",
        f"echo '{PASSWORD}' | sudo -S chmod -R 775 /home/{USERNAME}/apps/production-report"
    ]
    
    for cmd in cmds:
        stdin, stdout, stderr = client.exec_command(cmd)
        print(stdout.read().decode())
        err = stderr.read().decode()
        if err:
             print(f"Error executing '{cmd}': {err}")
             
    client.close()
    
    print("Permissions and directories fixed. Deploying...")
    # Now run the deploy_193.py script locally
    os.system("python deploy_193.py")

if __name__ == "__main__":
    prepare_env_and_deploy()
