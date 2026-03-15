import paramiko

def fetch_logs():
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect("192.168.1.79", username="administrador", password="GRW7czL3*")
        
        print("Fetching docker logs for production-report...")
        stdin, stdout, stderr = client.exec_command("docker logs --tail 200 production-report")
        
        logs = stdout.read().decode()
        if logs:
            print("LOGS:")
            # print only the lines with 'Error', 'Exception', '/api/support', or 500
            for line in logs.split('\n'):
                if 'api/support' in line or 'Error' in line or 'Exception' in line or '500' in line:
                    print(line.strip())
        
        err_logs = stderr.read().decode()
        if err_logs:
            print("ERR_LOGS:")
            for line in err_logs.split('\n'):
                if 'api/support' in line or 'Error' in line or 'Exception' in line or '500' in line:
                    print(line.strip())

        client.close()
    except Exception as e:
        print(f"Failed to fetch logs: {e}")

if __name__ == "__main__":
    fetch_logs()
