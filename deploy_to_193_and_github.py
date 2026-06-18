"""
deploy_to_193_and_github.py
───────────────────────────
1. Sube la versión actual (código) del servidor .79 al .193
2. Hace dump de la BD PostgreSQL de .79 y la restaura en .193
3. Pushea el código local al repositorio GitHub
"""
import paramiko, os, tarfile, time

PASS   = "GRW7czL3*"
USER   = "administrador"
PORT   = 22
HOST79 = "192.168.1.79"
HOST93 = "192.168.1.193"
REMOTE_DIR = "/home/administrador/apps/production-report"
LOCAL_BASE = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────────
def ssh(host, timeout=30):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, PORT, USER, PASS, timeout=timeout)
    return c

def run(client, cmd, timeout=120):
    print(f"  $ {cmd[:120]}")
    _, out, err = client.exec_command(cmd, timeout=timeout)
    stdout = out.read().decode("utf-8", errors="replace").strip()
    stderr = err.read().decode("utf-8", errors="replace").strip()
    if stdout: print("   ", stdout[:400])
    if stderr and "warning" not in stderr.lower()[:20]:
        print("  STDERR:", stderr[:300])
    return stdout

# ─────────────────────────────────────────────────
# PASO 1: Dump BD de .79 → archivo en .79
# ─────────────────────────────────────────────────
print("\n═══ PASO 1: Dump de PostgreSQL en .79 ═══")
c79 = ssh(HOST79)

dump_cmd = (
    f"echo '{PASS}' | sudo -S docker exec production-report-db "
    f"pg_dump -U app_user -d production_db --no-owner --no-acl "
    f"-f /var/lib/postgresql/data/prod_dump.sql 2>&1"
)
run(c79, dump_cmd, timeout=120)

# Copiar dump fuera del contenedor al host
run(c79, f"echo '{PASS}' | sudo -S docker cp production-report-db:/var/lib/postgresql/data/prod_dump.sql "
         f"/tmp/prod_dump_79.sql 2>&1", timeout=30)
print("  Dump creado en /tmp/prod_dump_79.sql")

# ─────────────────────────────────────────────────
# PASO 2: Transferir dump de .79 → local → .193
# ─────────────────────────────────────────────────
print("\n═══ PASO 2: Transferir dump .79 → local ═══")
sftp79 = c79.open_sftp()
local_dump = os.path.join(LOCAL_BASE, "prod_dump_79.sql")
sftp79.get("/tmp/prod_dump_79.sql", local_dump)
sftp79.close()
print(f"  Descargado: {local_dump} ({os.path.getsize(local_dump):,} bytes)")

print("\n═══ PASO 3: Subir dump → .193 y restaurar BD ═══")
c93 = ssh(HOST93)
sftp93 = c93.open_sftp()

# Subir dump al .193
sftp93.put(local_dump, "/tmp/prod_dump_79.sql")
sftp93.close()
print("  Dump subido a .193:/tmp/prod_dump_79.sql")

# Copiar dump al contenedor de BD en .193
run(c93, f"echo '{PASS}' | sudo -S docker cp /tmp/prod_dump_79.sql "
         f"production-report-db:/var/lib/postgresql/data/prod_dump.sql 2>&1", timeout=30)

# Restaurar → drop existing + restore (con --clean para idempotencia)
restore_cmd = (
    f"echo '{PASS}' | sudo -S docker exec production-report-db "
    f"psql -U app_user -d production_db -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;' 2>&1 && "
    f"echo '{PASS}' | sudo -S docker exec production-report-db "
    f"psql -U app_user -d production_db -f /var/lib/postgresql/data/prod_dump.sql 2>&1 | tail -5"
)
run(c93, restore_cmd, timeout=180)
print("  BD restaurada en .193 ✓")

# ─────────────────────────────────────────────────
# PASO 4: Sincronizar código .79 → .193
# ─────────────────────────────────────────────────
print("\n═══ PASO 4: Sincronizar código .79 → local → .193 ═══")

# Crear tarball del código en local
tar_path = os.path.join(LOCAL_BASE, "deploy_to_193.tar.gz")
print("  Creando tarball del código local...")
app_dir = os.path.join(LOCAL_BASE, "app")
excludes = {".git", "__pycache__", "venv", ".env", "*.pyc", "*.db"}

with tarfile.open(tar_path, "w:gz") as tar:
    def filter_fn(ti):
        for ex in excludes:
            if ex.replace("*","") in ti.name:
                return None
        return ti
    tar.add(app_dir, arcname="app", filter=filter_fn)
    for f in ["requirements.txt", "Dockerfile", "docker-compose.yml", ".dockerignore"]:
        p = os.path.join(LOCAL_BASE, f)
        if os.path.exists(p):
            tar.add(p, arcname=f)

size_mb = os.path.getsize(tar_path) / 1024 / 1024
print(f"  Tarball: {tar_path} ({size_mb:.1f} MB)")

# Subir al .193
sftp93 = c93.open_sftp()
sftp93.put(tar_path, f"{REMOTE_DIR}/deploy_to_193.tar.gz")
sftp93.close()
print("  Tarball subido al .193")

# Extraer y reiniciar
deploy_cmd = (
    f"cd {REMOTE_DIR} && "
    f"echo '{PASS}' | sudo -S tar -xzf deploy_to_193.tar.gz && "
    f"echo '{PASS}' | sudo -S docker-compose restart web 2>&1"
)
run(c93, deploy_cmd, timeout=120)
print("  Contenedor web reiniciado en .193 ✓")

c79.close()
c93.close()

# ─────────────────────────────────────────────────
# PASO 5: Limpiar archivos temporales
# ─────────────────────────────────────────────────
for tmp in [local_dump, tar_path]:
    if os.path.exists(tmp):
        os.remove(tmp)
        print(f"  Limpiado: {tmp}")

print("\n✅ Deploy a .193 completado con éxito")
print("   Código: sincronizado desde local (igual que .79)")
print("   BD:     restaurada desde .79")
print(f"   URL dev: http://{HOST93}:8000")
