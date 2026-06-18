"""
Check backup SQLite DB for inventory records and compare with production.
"""
import sqlite3

conn = sqlite3.connect('production_193.db')

# List all tables
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
print("All tables in backup:", tables)
print()

# Find inventory-related tables
inv_tables = [t for t in tables if 'invent' in t.lower() or 'stock' in t.lower() or 'logistic' in t.lower()]
print("Logistics/Inventory tables:", inv_tables)
print()

for t in inv_tables:
    count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {t}: {count} rows")
    if count > 0 and 'invent' in t.lower():
        cols = [c[1] for c in conn.execute(f"PRAGMA table_info({t})").fetchall()]
        print(f"    Columns: {cols}")
        rows = conn.execute(f"SELECT * FROM {t} LIMIT 5").fetchall()
        for r in rows:
            print(f"    {r}")

conn.close()
