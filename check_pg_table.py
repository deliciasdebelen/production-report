import paramiko

def check_table():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("192.168.1.79", username="administrador", password="GRW7czL3*")
    
    stdin, stdout, stderr = client.exec_command("docker exec production-report-db psql -U app_user -d production_db -c '\d support_settings'")
    out = stdout.read().decode()
    err = stderr.read().decode()
    
    print("STDOUT:")
    print(out)
    if err:
        print("STDERR:")
        print(err)
    
    client.close()

if __name__ == "__main__":
    check_table()
