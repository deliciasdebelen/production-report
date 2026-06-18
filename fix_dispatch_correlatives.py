"""
Fix dispatch guide (document_ref) correlatives in production.

PROBLEM: 
- Records were imported from backup (193 server) mixed with natural records.
- The DB_ID (row id) does NOT match chronological order.
- Records with IDs 1-60 have dates from Jan-Feb 2026 (mixed with natural records)
- Records with IDs 61-63 are today (Mar 17) - natural.
- Records with IDs 64-133 are Feb-March 2026 (also natural, created after the backup import)

GOAL: Reassign document_ref (GUIA-XXXXXXXX) to reflect CHRONOLOGICAL ORDER.
Every record gets the GUIA number corresponding to its position
when all records are sorted by date ascending.

SAFETY: This only updates document_ref field. No records are deleted.
"""
import sys
sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models import LogisticsDispatch
from sqlalchemy import text
import re

db = SessionLocal()

print("=== DISPATCH CORRELATIVE FIXER ===")
print()

# Get ALL records ordered by DATE ascending
records = db.query(LogisticsDispatch).order_by(LogisticsDispatch.date.asc()).all()
total = len(records)
print(f"Total records to process: {total}")
print()

# Show current state - first 10 by date
print("--- Current state (first 10 by date) ---")
for r in records[:10]:
    print(f"  DB_ID={r.id:4d}  date={str(r.date)[:19]}  ref={r.document_ref[:40] if r.document_ref else 'None'}")
print("  ...")

print()
print("--- Current state (last 10 by date) ---")
for r in records[-10:]:
    print(f"  DB_ID={r.id:4d}  date={str(r.date)[:19]}  ref={r.document_ref[:40] if r.document_ref else 'None'}")

print()
print("--- Planned new assignments ---")

changes = []
for new_seq, record in enumerate(records, start=1):
    old_ref = record.document_ref or ''
    
    # Extract the part after the GUIA number (the " | Fact: ..." part)
    if '|' in old_ref:
        fact_part = old_ref[old_ref.index('|'):]
    else:
        fact_part = ''
    
    new_ref = f"GUIA-{new_seq:08d} {fact_part}".rstrip()
    
    if old_ref != new_ref:
        changes.append((record.id, old_ref, new_ref))
        if new_seq <= 10 or new_seq >= total - 5:
            print(f"  DB_ID={record.id:4d}  SEQ={new_seq:4d}  {old_ref[:30]!s:32s} -> {new_ref[:30]}")

print(f"\nTotal records needing update: {len(changes)}")
print()

# Confirm before applying
confirm = input("Apply changes? (yes/no): ").strip().lower()
if confirm != 'yes':
    print("Aborted.")
    db.close()
    sys.exit(0)

print("Applying changes...")
updated = 0

for record in records:
    old_ref = record.document_ref or ''
    
    if '|' in old_ref:
        fact_part = old_ref[old_ref.index('|'):]
    else:
        fact_part = ''
    
    # Get sequential position (1-indexed among all records by date)
    seq = records.index(record) + 1
    new_ref = f"GUIA-{seq:08d} {fact_part}".rstrip()
    
    if record.document_ref != new_ref:
        record.document_ref = new_ref
        updated += 1

db.commit()
print(f"✅ Updated {updated} records.")

# Verify
print()
print("--- Verification (first 10 by date after update) ---")
records_after = db.query(LogisticsDispatch).order_by(LogisticsDispatch.date.asc()).limit(10).all()
for r in records_after:
    print(f"  DB_ID={r.id:4d}  date={str(r.date)[:19]}  ref={r.document_ref[:50] if r.document_ref else 'None'}")

print()
print("--- Verification (last 10 by date after update) ---")
records_end = db.query(LogisticsDispatch).order_by(LogisticsDispatch.date.desc()).limit(10).all()
for r in records_end:
    print(f"  DB_ID={r.id:4d}  date={str(r.date)[:19]}  ref={r.document_ref[:50] if r.document_ref else 'None'}")

db.close()
print("\nDone.")
