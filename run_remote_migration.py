import paramiko

def run_migration_remotely():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("192.168.1.79", username="administrador", password="GRW7czL3*")
    
    cmd = "docker exec production-report python /app/app/migrate_projects.py"
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
    run_migration_remotely()
