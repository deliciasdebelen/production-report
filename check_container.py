import paramiko

def check_logs():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("192.168.1.79", username="administrador", password="GRW7czL3*")
    
    cmd = "docker logs --tail 200 production-report"
    print(f"Executing: {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    
    out = stdout.read().decode()
    err = stderr.read().decode()
    
    print("OUTPUT:")
    print(out)
    if err:
        print("ERROR:")
        print(err)
        
    client.close()

if __name__ == "__main__":
    check_logs()
