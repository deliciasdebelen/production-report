import sqlite3

db_path = 'production.db'
con = sqlite3.connect(db_path)
cur = con.cursor()

def get_columns(table):
    cur.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in cur.fetchall()]

print("--- Production Reports Columns ---")
print(get_columns('production_reports'))

print("\n--- Production Planning Columns ---")
print(get_columns('production_planning'))

print("\n--- Logistics Tables ---")
try:
    print("Reception Production:", get_columns('logistics_reception_production'))
except: print("Error logistics_reception_production")

con.close()
