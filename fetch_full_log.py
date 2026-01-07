
import paramiko

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"

def main():
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOSTNAME, 22, USERNAME, PASSWORD)
        
        cmd = "docker logs --tail 500 production-report"
        print(f"Executing: {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd)
        
        with open("full_log.txt", "w", encoding="utf-8") as f:
            f.write(stdout.read().decode())
            f.write(stderr.read().decode())
            
        client.close()
        print("Log saved to full_log.txt")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
