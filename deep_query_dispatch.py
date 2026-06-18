"""
Detailed production query:
- Total count, max ID, max GUIA number
- Last 10 records by DATE (most recent first)
- Records around ID 60-70 (to see what's natural vs imported)
- Records where document_ref has high GUIA number (36-133)
"""
import sys
sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models import LogisticsDispatch
import json
from datetime import datetime

db = SessionLocal()

# 1. Stats
total = db.query(LogisticsDispatch).count()
max_id = db.query(LogisticsDispatch.id).order_by(LogisticsDispatch.id.desc()).first()
min_id = db.query(LogisticsDispatch.id).order_by(LogisticsDispatch.id.asc()).first()

print(f"TOTAL RECORDS: {total}")
print(f"MAX ID: {max_id[0] if max_id else None}")
print(f"MIN ID: {min_id[0] if min_id else None}")

# 2. Last 10 by date
print("\n--- LAST 10 BY DATE ---")
recent = db.query(LogisticsDispatch).order_by(LogisticsDispatch.date.desc()).limit(10).all()
for r in recent:
    ref_short = (r.document_ref or '')[:50]
    print(f"  ID={r.id}  date={str(r.date)[:19]}  ref={ref_short}")

# 3. First 10 by ID
print("\n--- FIRST 10 BY ID ---")
first = db.query(LogisticsDispatch).order_by(LogisticsDispatch.id.asc()).limit(10).all()
for r in first:
    ref_short = (r.document_ref or '')[:50]
    print(f"  ID={r.id}  date={str(r.date)[:19]}  ref={ref_short}")

# 4. IDs around 60-70
print("\n--- IDs 55 to 70 ---")
mid = db.query(LogisticsDispatch).filter(
    LogisticsDispatch.id >= 55,
    LogisticsDispatch.id <= 70
).order_by(LogisticsDispatch.id).all()
for r in mid:
    ref_short = (r.document_ref or '')[:60]
    print(f"  ID={r.id}  date={str(r.date)[:19]}  ref={ref_short}")

# 5. All document_refs and extract GUIA numbers
print("\n--- GUIA NUMBER DISTRIBUTION ---")
all_refs = db.query(LogisticsDispatch.id, LogisticsDispatch.document_ref, LogisticsDispatch.date).order_by(LogisticsDispatch.id).all()

def get_guia_num(ref):
    if not ref:
        return None
    try:
        return int(ref.split('|')[0].strip().split('-')[1])
    except:
        return None

guia_nums = [(r.id, get_guia_num(r.document_ref), str(r.date)[:19], r.document_ref[:40] if r.document_ref else '') for r in all_refs]

# Find max GUIA
max_guia = max((g[1] for g in guia_nums if g[1] is not None), default=None)
print(f"Max GUIA correlative: {max_guia}")

# Check for duplicates
from collections import Counter
guia_count = Counter(g[1] for g in guia_nums if g[1] is not None)
dupes = {k: v for k, v in guia_count.items() if v > 1}
if dupes:
    print(f"DUPLICATE GUIA NUMBERS: {sorted(dupes.keys())}")
else:
    print("No duplicate GUIA numbers found.")

# Show all IDs vs GUIA number as a table
print("\n--- ALL ID vs GUIA NUMBER vs DATE ---")
for db_id, guia_num, date, ref in guia_nums:
    print(f"  DB_ID={db_id:4d}  GUIA={guia_num!s:5}  date={date}  ref_prefix={ref}")

db.close()
