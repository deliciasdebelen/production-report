import paramiko

def run_db_fix():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("192.168.1.79", username="administrador", password="GRW7czL3*")
    
    cmd = 'docker exec production-report-db psql -U app_user -d production_db -c "ALTER TABLE project_cards ADD COLUMN due_date TIMESTAMP WITH TIME ZONE NULL;"'
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
    run_db_fix()
