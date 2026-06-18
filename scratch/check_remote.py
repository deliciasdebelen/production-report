import paramiko

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"

def run_remote():
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOSTNAME, 22, USERNAME, PASSWORD)
        
        commands = [
            "cd /home/administrador/apps/production-report && git stash show -p stash@{0} || true",
            "cd /home/administrador/apps/production-report && git stash show -p stash@{1} || true",
            "cd /home/administrador/apps/production-report && git stash show -p stash@{2} || true"
        ]
        
        output_file = "/Users/cesarvasquez/Documents/Proyectos/Projects/production-report/scratch/remote_stash_show.txt"
        with open(output_file, "w") as f:
            for cmd in commands:
                f.write("="*80 + "\n")
                f.write(f"COMMAND: {cmd}\n")
                f.write("="*80 + "\n")
                stdin, stdout, stderr = client.exec_command(cmd)
                out = stdout.read().decode('utf-8', errors='replace')
                err = stderr.read().decode('utf-8', errors='replace')
                if out:
                    f.write(out + "\n")
                if err:
                    f.write(f"STDERR: {err}\n")
        print(f"Output saved to {output_file}")
        client.close()
    except Exception as e:
        print(f"Error connecting or executing: {e}")

if __name__ == "__main__":
    run_remote()
