import paramiko
import os

def upload_and_run():
    try:
        print("Connecting to 192.168.1.79...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect("192.168.1.79", 22, "administrador", "GRW7czL3*")
        
        sftp = client.open_sftp()
        print("Uploading data...")
        sftp.put("logistics_data_193.json", "/home/administrador/apps/production-report/app/logistics_data_193.json")
        sftp.put("docker_inject.py", "/home/administrador/apps/production-report/app/docker_inject.py")
        sftp.close()
        
        print("Running injection script inside Docker...")
        command = 'docker-compose exec -T web python app/docker_inject.py'
        stdin, stdout, stderr = client.exec_command(f"cd ~/apps/production-report && {command}")
        
        print("STDOUT:")
        print(stdout.read().decode())
        print("STDERR:")
        print(stderr.read().decode())
        
        client.close()
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    upload_and_run()
