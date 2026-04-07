import paramiko
import json

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.79', username='administrador', password='GRW7czL3*')

print("=== DOCKER INSPECT kanban worker ===")
stdin, stdout, stderr = client.exec_command("docker inspect production-report-kanban-worker")
out = stdout.read().decode()
try:
    data = json.loads(out)
    if data and len(data) > 0:
        mounts = data[0].get("Mounts", [])
        for m in mounts:
            print(f"Mount: {m.get('Source')} -> {m.get('Destination')}")
except Exception as e:
    print("Error parsing inspect:", e)
    print(out[:500])

client.close()
