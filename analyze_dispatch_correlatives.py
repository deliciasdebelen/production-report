"""
Comparison script: reads production dispatch from JSON file + backup sqlite
Then does full analysis
"""
import sqlite3
import json

# ---- Load production data from file ----
# Read the JSON file with proper encoding handling
with open('production_dispatch.json', 'rb') as f:
    raw_bytes = f.read()

# Try to detect encoding
if raw_bytes[:2] == b'\xff\xfe':
    # UTF-16 LE
    raw = raw_bytes.decode('utf-16-le').strip()
elif raw_bytes[:3] == b'\xef\xbb\xbf':
    # UTF-8 BOM
    raw = raw_bytes[3:].decode('utf-8').strip()
else:
    raw = raw_bytes.decode('utf-8', errors='replace').strip()

# Strip any SSHpass prompt lines
if '[' in raw:
    raw = raw[raw.find('['):]
if raw.endswith('\r\n'):
    raw = raw.rstrip()

prod_rows = json.loads(raw)

# ---- Load backup data ----
conn = sqlite3.connect('production_193.db')
backup_rows = conn.execute(
    "SELECT id, document_ref, client_destination, date FROM logistics_dispatch ORDER BY id"
).fetchall()
conn.close()

print("=" * 70)
print(f"BACKUP RECORDS:     {len(backup_rows)}")
print(f"PRODUCTION RECORDS: {len(prod_rows)}")
print("=" * 70)

# Build maps
backup_refs = {r[1]: r for r in backup_rows if r[1]}
prod_refs = {r['ref']: r for r in prod_rows if r.get('ref')}

# Extract numeric correlative from ref like "GUIA-00000001 | ..."
def extract_guia_num(ref):
    if not ref:
        return None
    try:
        part = ref.split('|')[0].strip()  # "GUIA-00000001"
        num = int(part.split('-')[1].strip())
        return num
    except Exception:
        return None

backup_nums = sorted([extract_guia_num(r[1]) for r in backup_rows if extract_guia_num(r[1]) is not None])
prod_nums = sorted([extract_guia_num(r['ref']) for r in prod_rows if extract_guia_num(r.get('ref')) is not None])

max_backup_num = max(backup_nums) if backup_nums else 0
max_prod_num = max(prod_nums) if prod_nums else 0
min_prod_num = min(prod_nums) if prod_nums else 0

print(f"\nBackup  GUIA range: {min(backup_nums)} → {max_backup_num}")
print(f"Prod    GUIA range: {min_prod_num} → {max_prod_num}")

# Which backup records are missing in production?
missing = [(r[0], r[1], r[2], r[3]) for r in backup_rows if r[1] not in prod_refs]

print(f"\nRecords in BACKUP not in PRODUCTION: {len(missing)}")
for r in missing:
    print(f"  Backup ID={r[0]}  ref={r[1]}  client={r[2]}  date={r[3]}")

if not missing:
    print("  → All backup records exist in production. Production is ahead.")

print("\n" + "=" * 70)
print("CONCLUSION:")

if max_backup_num > max_prod_num:
    print(f"⚠️  BACKUP has more guide history (max={max_backup_num}) than PRODUCTION (max={max_prod_num}).")
    print(f"   {len(missing)} records from the backup are missing from production.")
    print("   Action required: insert the missing records with corrected correlatives.")
elif max_prod_num >= max_backup_num:
    print(f"✅  PRODUCTION is at position {max_prod_num}, backup at {max_backup_num}.")
    if missing:
        print(f"   But {len(missing)} backup records are missing from production (possibly different ref format).")
    else:
        print("   No action needed.")
