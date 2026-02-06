import paramiko

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22
REMOTE_FILE = "/home/administrador/apps/production-report/app/routers/logistics.py"

def check_remote_file():
    print(f"--- Checking Remote File: {REMOTE_FILE} ---")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)
        
        # Read file content
        cmd = f"cat {REMOTE_FILE}"
        stdin, stdout, stderr = client.exec_command(cmd)
        
        content = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        
        if err:
            print(f"Error reading file: {err}")
        else:
            # Check for the fix signatures
            print(f"File Size: {len(content)} bytes")
            
            if 'request: Request' in content and 'form_data = await request.form()' in content:
                print("✅ FIX FOUND: 'Nuclear Bypass' (Request object) is present.")
            elif 'client_destination: str = Form("")' in content:
                print("⚠️ PARTIAL FIX: 'Relaxed Validation' (str = Form(\"\")) is present.")
            elif 'client_destination: Optional[str] = Form(None)' in content:
                 print("⚠️ OLDER FIX: 'Optional' is present.")
            else:
                 print("❌ FIX MISSING: File appears to depend on strict Pydantic validation for client_destination.")

            # Print relevant snippet
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'def create_dispatch' in line:
                    print("\n--- Snippet ---")
                    print('\n'.join(lines[i:i+15]))
                    break
        
        client.close()
            
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    check_remote_file()
