import paramiko, requests

HOST79, USER, PASS = "192.168.1.79", "administrador", "GRW7czL3*"

# 1. Probar el endpoint DELETE directamente via HTTP (con sesión autenticada)
s = requests.Session()
login = s.post("http://192.168.1.79:8000/login", data={"username": "admin", "password": "admin"}, allow_redirects=True, timeout=10)
print("Login status:", login.status_code, login.url)

# Obtener un list_id real
list_id = "20260405-f9a421e0"  # "Por Hacer" del tablero de prueba
resp = s.delete(f"http://192.168.1.79:8000/api/projects/lists/{list_id}", timeout=10)
print(f"DELETE /api/projects/lists/{list_id} -> {resp.status_code}: {resp.text[:200]}")

# 2. Verificar que el board.html del servidor tiene la firma correcta de deleteList
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST79, 22, USER, PASS)
_, out, _ = c.exec_command(f"grep -n 'deleteList' /home/administrador/apps/production-report/app/templates/projects/board.html 2>&1")
print("\n=== deleteList en board.html del servidor ===")
print(out.read().decode("utf-8", errors="replace").strip())
c.close()
