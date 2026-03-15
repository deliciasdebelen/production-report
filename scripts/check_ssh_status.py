import paramiko

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"

def check_remote_status():
    print(f"Connecting to {HOSTNAME} via SSH...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOSTNAME, port=22, username=USERNAME, password=PASSWORD)
        
        print("SUCCESS: Connected to server!")
        
        # Check docker containers
        print("\n--- Container Status ---")
        stdin, stdout, stderr = client.exec_command("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
        print(stdout.read().decode())
        
        # Check logs of the migration if possible (by running a check script inside the container)
        print("\n--- DB Table Counts (via docker exec) ---")
        # Command to check postgres inside the container
        check_cmd = r"""docker exec production-report python3 -c "import sqlalchemy; from sqlalchemy import create_engine, text; engine = create_engine('postgresql://app_user:production_password@db:5432/production_db');
with engine.connect() as conn:
    for t in ['users', 'roles', 'production_reports', 'production_planning']:
        count = conn.execute(text('SELECT COUNT(*) FROM ' + t)).scalar()
        print(f'{t}: {count}')" """
        
        stdin, stdout, stderr = client.exec_command(check_cmd)
        print(stdout.read().decode())
        
        # Check Audit Status
        print("\n--- Audit Diagnostics (via StockSolver) ---")
        audit_cmd = r"""docker exec production-report python3 -c "from app.services.stock_solver import StockSolver; issues = StockSolver.get_diagnostics(); print(f'Total issues: {len(issues)}'); tras_issues = [i for i in issues if i['type'] == 'TRANSFER_WITHOUT_MOVEMENT']; print(f'Transfers without movement: {len(tras_issues)}')" """
        stdin, stdout, stderr = client.exec_command(audit_cmd)
        print(stdout.read().decode())
        err = stderr.read().decode()
        if err: print(f"STDERR: {err}")
        
        client.close()
    except Exception as e:
        print(f"FAILURE: {e}")

if __name__ == "__main__":
    check_remote_status()
