import paramiko

def run_migration():
    try:
        print("Connecting to 192.168.1.79...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect("192.168.1.79", 22, "administrador", "GRW7czL3*")
        
        print("Running migrate_dispatch.py inside docker container...")
        command = 'docker-compose exec -T web python -c "import sys; sys.path.append(\'/app\'); from app import models; from sqlalchemy import create_engine; engine = create_engine(\'sqlite:////app/production.db\'); models.Base.metadata.create_all(bind=engine)"'
        stdin, stdout, stderr = client.exec_command(f"cd ~/apps/production-report && {command}")
        
        # In case it's not named 'web', let's also try running it outside directly
        # if the above fails.
        
        client.close()
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    run_migration()
