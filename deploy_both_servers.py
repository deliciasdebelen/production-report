import paramiko, os, sys

def deploy_to(host, label):
    HOST, USER, PASS = host, "administrador", "GRW7czL3*"
    REMOTE_DIR = "/home/administrador/apps/production-report"
    LOCAL_BASE = r"c:\Users\ovargas\Projects\production-report"

    files = [
        (r"app\templates\projects\board.html",  REMOTE_DIR + "/app/templates/projects/board.html"),
        (r"app\templates\projects\detail.html", REMOTE_DIR + "/app/templates/projects/detail.html"),
        (r"app\routers\projects.py",            REMOTE_DIR + "/app/routers/projects.py"),
    ]

    print(f"\nDeploy -> {label} ({host})")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, 22, USER, PASS)
    sftp = c.open_sftp()
    for local_rel, remote in files:
        sftp.put(os.path.join(LOCAL_BASE, local_rel), remote)
        print(f"  OK: {local_rel}")
    sftp.close()

    _, out, _ = c.exec_command(
        f'echo "{PASS}" | sudo -S docker restart production-report 2>&1', timeout=70
    )
    lines = out.read().decode("ascii", errors="replace").strip().split("\n")
    print("  Restart:", lines[-1])
    c.close()
    print(f"  Done: {label}")

deploy_to("192.168.1.79",  "PRODUCCION")
deploy_to("192.168.1.193", "DESARROLLO")
print("\nAmbos servidores actualizados.")
