import paramiko
import os

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
    sftp = client.open_sftp()
    
    # 1. Upload fixed management.html
    local_path = "../Projects/production-report/prod_management.html"
    remote_tmp_path = "/tmp/support_patch/app/templates/support/management.html"
    
    print(f"Uploading fixed management.html...")
    sftp.put(local_path, remote_tmp_path)
    sftp.close()
    
    # 2. Copy to container
    print("Copying to container...")
    cmd = f'echo "{PASSWORD}" | sudo -S docker cp {remote_tmp_path} production-report:/app/app/templates/support/management.html'
    client.exec_command(cmd)
    
    # 3. Restore Email configuration in DB
    query = "UPDATE support_settings SET notification_emails = 'sistemas@deliciasdebelen.com, soporte@deliciasdebelen.com', cc_emails = '', smtp_user = 'sistemas@deliciasdebelen.com';"
    print("Restoring support_settings in database...")
    cmd2 = f'echo "{PASSWORD}" | sudo -S docker exec production-report-db psql -U app_user -d production_db -c "{query}"'
    client.exec_command(cmd2)
    
    # 4. Restart container
    print("Restarting production-report container...")
    cmd3 = f'echo "{PASSWORD}" | sudo -S docker restart production-report'
    client.exec_command(cmd3)
    
    client.close()
    print("Patch and restore completed.")

if __name__ == "__main__":
    run()
