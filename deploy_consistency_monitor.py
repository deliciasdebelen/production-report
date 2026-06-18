import paramiko
import os
import tarfile
import sys

def create_tarball(output_filename):
    print(f"Creating tarball {output_filename} of consistency-monitor...")
    with tarfile.open(output_filename, "w:gz") as tar:
        # We pack the contents of consistency-monitor/ folder
        source_dir = "consistency-monitor"
        if not os.path.exists(source_dir):
            print(f"Error: {source_dir} directory not found.")
            sys.exit(1)
        
        excludes = ['__pycache__', '.venv', '.env']
        
        def filter_func(tarinfo):
            for excl in excludes:
                if excl in tarinfo.name:
                    return None
            return tarinfo
            
        tar.add(source_dir, arcname=".", filter=filter_func)

def deploy_to_host(hostname, port_mapping):
    username = "administrador"
    password = "GRW7czL3*"
    remote_dir = "/home/administrador/apps/consistency-monitor"
    tar_name = "consistency_monitor_deploy.tar.gz"
    
    try:
        create_tarball(tar_name)
        
        print(f"\n==========================================")
        print(f"Deploying to {hostname} (port={port_mapping})...")
        print(f"==========================================")
        
        transport = paramiko.Transport((hostname, 22))
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        # Ensure remote apps directory exists
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, 22, username, password)
        
        stdin, stdout, stderr = client.exec_command(f"mkdir -p {remote_dir}")
        stdout.read() # Wait for folder creation to complete
        
        print(f"Uploading {tar_name}...")
        sftp.put(tar_name, f"{remote_dir}/{tar_name}")
        sftp.close()
        transport.close()
        
        def run_cmd(cmd_str):
            print(f"Executing: {cmd_str}")
            stdin, stdout, stderr = client.exec_command(cmd_str)
            out = stdout.read().decode()
            err = stderr.read().decode()
            if out: print(out)
            if err: print(f"STDERR: {err}")
            return out, err

        # Deployment command
        # Build and run with PORT env variable
        deploy_cmd = (
            f"cd {remote_dir} && "
            f"tar -mxzf {tar_name} && "
            f"rm -f {tar_name} && "
            f"export PORT={port_mapping} && "
            f"(docker compose down || docker-compose down || true) && "
            f"(docker compose up -d --build || docker-compose up -d --build)"
        )
        
        run_cmd(deploy_cmd)
        client.close()
        print(f"Deployment to {hostname} finished successfully.")
        
    except Exception as e:
        print(f"Failed to deploy to {hostname}: {e}")
    finally:
        if os.path.exists(tar_name):
            os.remove(tar_name)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python deploy_consistency_monitor.py [staging|prod|all]")
        sys.exit(1)
        
    target = sys.argv[1].lower()
    
    # Change current working directory to script directory's parent to ensure consistency-monitor is visible
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    if target == "staging":
        deploy_to_host("192.168.1.193", 8005)
    elif target == "prod":
        deploy_to_host("192.168.1.79", 8002)
    elif target == "all":
        deploy_to_host("192.168.1.193", 8005)
        deploy_to_host("192.168.1.79", 8002)
    else:
        print("Invalid target. Choose: staging, prod, or all.")
