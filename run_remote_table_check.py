
import paramiko

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22
REMOTE_DIR = "/home/administrador/apps/production-report"

def run_remote():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOSTNAME, port=PORT, username=USERNAME, password=PASSWORD)
        
        # Upload
        sftp = client.open_sftp()
        sftp.put("check_table_list.py", f"{REMOTE_DIR}/check_table_list_remote.py")
        sftp.close()
        
        # Exec
        cmd = f"cd {REMOTE_DIR} && docker cp check_table_list_remote.py production-report:/app/check_table_list_remote.py && docker exec production-report python /app/check_table_list_remote.py"
        stdin, stdout, stderr = client.exec_command(cmd)
        
        print(stdout.read().decode())
        print(stderr.read().decode())

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    run_remote()
