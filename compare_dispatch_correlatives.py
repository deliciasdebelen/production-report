"""
Compare dispatch guide (document_ref) correlatives between:
 - Backup SQLite DB (production_193.db) 
 - Current production PostgreSQL on 192.168.1.79
"""
import sqlite3
import sys
import os

# ---- 1. Read from backup SQLite ----
LOCAL_DB = 'production_193.db'

print("=" * 60)
print("BACKUP DB:", LOCAL_DB)
print("=" * 60)

if not os.path.exists(LOCAL_DB):
    print(f"File not found: {LOCAL_DB}")
    sys.exit(1)

conn_backup = sqlite3.connect(LOCAL_DB)
backup_rows = conn_backup.execute(
    "SELECT id, document_ref, client_destination, date FROM logistics_dispatch ORDER BY id"
).fetchall()
conn_backup.close()

print(f"Total dispatch records in backup: {len(backup_rows)}")
if backup_rows:
    print("First:", backup_rows[0])
    print("Last:", backup_rows[-1])
    print("\nAll document_refs in backup:")
    for r in backup_rows:
        print(f"  ID={r[0]}  ref={r[1]}  client={r[2]}  date={r[3]}")

# ---- 2. Read from production PostgreSQL via SSH/API ----
print("\n" + "=" * 60)
print("PRODUCTION PostgreSQL on 192.168.1.79")
print("=" * 60)

# Use the app's database module
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app'))
try:
    from app.database import SessionLocal
    from app.models import LogisticsDispatch

    db = SessionLocal()
    prod_rows = db.query(
        LogisticsDispatch.id,
        LogisticsDispatch.document_ref,
        LogisticsDispatch.client_destination,
        LogisticsDispatch.date
    ).order_by(LogisticsDispatch.id).all()
    db.close()

    print(f"Total dispatch records in production: {len(prod_rows)}")
    if prod_rows:
        print("First:", prod_rows[0])
        print("Last:", prod_rows[-1])
        print("\nAll document_refs in production:")
        for r in prod_rows:
            print(f"  ID={r[0]}  ref={r[1]}  client={r[2]}  date={r[3]}")

    # ---- 3. Compare ----
    print("\n" + "=" * 60)
    print("COMPARISON")
    print("=" * 60)

    backup_refs = set(r[1] for r in backup_rows if r[1])
    prod_refs = set(str(r[1]) for r in prod_rows if r[1])

    in_backup_not_prod = backup_refs - prod_refs
    in_prod_not_backup = prod_refs - backup_refs

    print(f"Refs in backup but NOT in production: {sorted(in_backup_not_prod)}")
    print(f"Refs in production but NOT in backup: {sorted(in_prod_not_backup)}")

    if len(backup_rows) > len(prod_rows):
        print(f"\n⚠️  Backup has MORE records ({len(backup_rows)}) than production ({len(prod_rows)})")
    elif len(backup_rows) < len(prod_rows):
        print(f"\nℹ️  Production has more records ({len(prod_rows)}) than backup ({len(backup_rows)})")
    else:
        print(f"\n✅  Same number of records ({len(backup_rows)})")

except Exception as e:
    print(f"Error connecting to production DB: {e}")
    print("\nTrying via direct SSH query instead...")
    import subprocess
    result = subprocess.run(
        ['python', 'diagnose_remote_db.py'],
        capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__))
    )
    print(result.stdout)
    print(result.stderr)
