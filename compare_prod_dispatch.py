"""
Query production PostgreSQL via SSH to get dispatch records.
Compares with backup 193 SQLite DB.
"""
import subprocess
import sqlite3
import json

REMOTE_USER = "administrador"
REMOTE_IP = "192.168.1.79"
REMOTE_PASS = "GRW7czL3*"

# SSH command to query psql inside Docker container
ssh_cmd = f"""sshpass -p '{REMOTE_PASS}' ssh -o StrictHostKeyChecking=no {REMOTE_USER}@{REMOTE_IP} "docker exec production-report python -c \\"
import sys
sys.path.insert(0, '/app')
from app.database import SessionLocal
db = SessionLocal()
from app.models import LogisticsDispatch
rows = db.query(LogisticsDispatch.id, LogisticsDispatch.document_ref, LogisticsDispatch.client_destination, LogisticsDispatch.date).order_by(LogisticsDispatch.id).all()
import json
data = [{'id': r.id, 'ref': r.document_ref, 'client': r.client_destination, 'date': str(r.date)} for r in rows]
print(json.dumps(data))
db.close()
\\""
"""

print("Querying production server via SSH...")
result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True, timeout=60)

if result.returncode != 0:
    print("SSH Error:", result.stderr)
    # Try alternative: just exec python script inside container
    inner_py = """import sys
sys.path.insert(0, '/app')
from app.database import SessionLocal
from app.models import LogisticsDispatch
db = SessionLocal()
rows = db.query(LogisticsDispatch.id, LogisticsDispatch.document_ref, LogisticsDispatch.client_destination, LogisticsDispatch.date).order_by(LogisticsDispatch.id).all()
import json
data = [{'id': r.id, 'ref': r.document_ref, 'client': r.client_destination, 'date': str(r.date)} for r in rows]
print(json.dumps(data))
db.close()"""
    
    with open('/tmp/query_prod.py', 'w') as f:
        f.write(inner_py)
    
    result2 = subprocess.run(
        f"sshpass -p '{REMOTE_PASS}' scp -o StrictHostKeyChecking=no /tmp/query_prod.py {REMOTE_USER}@{REMOTE_IP}:/tmp/query_prod.py",
        shell=True, capture_output=True, text=True
    )
    result3 = subprocess.run(
        f"sshpass -p '{REMOTE_PASS}' ssh -o StrictHostKeyChecking=no {REMOTE_USER}@{REMOTE_IP} 'docker cp /tmp/query_prod.py production-report:/tmp/query_prod.py && docker exec production-report python /tmp/query_prod.py'",
        shell=True, capture_output=True, text=True, timeout=60
    )
    if result3.returncode == 0:
        result = result3
    else:
        print("Docker exec error:", result3.stderr)
        exit(1)

stdout = result.stdout.strip()
if not stdout:
    print("No output from production server")
    exit(1)

# Parse JSON output
try:
    prod_rows = json.loads(stdout)
    print(f"\nProduction records: {len(prod_rows)}")
    for r in prod_rows:
        print(f"  ID={r['id']}  ref={r['ref']}  client={r['client']}  date={r['date']}")
except Exception as e:
    print("Error parsing output:", e)
    print("Raw output:", stdout[:2000])
    exit(1)

# ------- Compare with backup -------
print("\n" + "=" * 60)
conn = sqlite3.connect('production_193.db')
backup_rows = conn.execute(
    "SELECT id, document_ref, client_destination, date FROM logistics_dispatch ORDER BY id"
).fetchall()
conn.close()

print(f"Backup records:     {len(backup_rows)}")
print(f"Production records: {len(prod_rows)}")

backup_refs = [(r[0], r[1]) for r in backup_rows if r[1]]
prod_refs = set(r['ref'] for r in prod_rows if r.get('ref'))

print("\nGuias en backup NO presentes en producción:")
missing = [(id_, ref) for id_, ref in backup_refs if ref not in prod_refs]
for id_, ref in missing:
    print(f"  Backup ID={id_}  ref={ref}")

if not missing:
    print("  [Ninguna - todos los registros del backup existen en producción]")

# Max IDs
max_backup_id = max(r[0] for r in backup_rows) if backup_rows else 0
max_prod_id = max(int(r['id']) for r in prod_rows) if prod_rows else 0
print(f"\nMax ID backup: {max_backup_id}")
print(f"Max ID prod:   {max_prod_id}")
