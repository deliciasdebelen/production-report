import subprocess

print("Copiando test_support.py al contenedor...")
cmd1 = 'echo "GRW7czL3*" | sudo -S docker cp ../Projects/production-report/test_support.py production-report:/app/test_support.py'
subprocess.run(cmd1, shell=True)

print("Ejecutando test_support.py dentro del contenedor...")
cmd2 = 'echo "GRW7czL3*" | sudo -S docker exec production-report python /app/test_support.py'
res = subprocess.run(cmd2, shell=True, text=True, capture_output=True)

print(res.stdout)
if res.stderr:
    print("ERRORS:", res.stderr)
