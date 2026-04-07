import paramiko
import os
import sqlite3
from sqlalchemy import create_engine, text

local_db_path = 'production_remote.db'

print("Downloading data/production.db via SFTP...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.79', username='administrador', password='GRW7czL3*')

sftp = client.open_sftp()
try:
    sftp.get('/home/administrador/apps/production-report/data/production.db', local_db_path)
    print("Download complete.")
except Exception as e:
    print("Failed to download:", e)
    sftp.close()
    client.close()
    exit(1)
sftp.close()
client.close()

print("Connecting to local SQLite DB copy...")
sqlite_conn = sqlite3.connect(local_db_path)
sqlite_conn.row_factory = sqlite3.Row

print("Connecting to live remote PostgreSQL DB...")
pg_engine = create_engine("postgresql://app_user:production_password@192.168.1.79:5434/production_db")

cur_sqlite = sqlite_conn.cursor()
cur_sqlite.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != 'alembic_version'")
tables = [row['name'] for row in cur_sqlite.fetchall()]

missing_records_total = 0

print(f"{'Table Name'.ljust(35)} | {'Missing IDs'}")
print("-" * 60)

with pg_engine.connect() as pg_conn:
    for table in tables:
        # Check if table has an 'id' column
        cur_sqlite.execute(f'PRAGMA table_info("{table}")')
        columns = [col['name'] for col in cur_sqlite.fetchall()]
        
        if 'id' not in columns:
            print(f"{table.ljust(35)} | Skipped (No 'id' column PK)")
            continue
            
        cur_sqlite.execute(f"SELECT id FROM '{table}'")
        sqlite_ids = set()
        for row in cur_sqlite.fetchall():
            sqlite_ids.add(row['id'])
        
        if not sqlite_ids:
            print(f"{table.ljust(35)} | 0 missing (Table is empty)")
            continue
            
        try:
            res = pg_conn.execute(text(f'SELECT id FROM "{table}"')).fetchall()
            pg_ids = {row[0] for row in res}
        except Exception as e:
            pg_conn.rollback()
            print(f"{table.ljust(35)} | ERROR querying PostgreSQL")
            continue
            
        missing_ids = sqlite_ids - pg_ids
        missing_count = len(missing_ids)
        missing_records_total += missing_count
        
        if missing_count > 0:
            print(f"{table.ljust(35)} | ❌ {missing_count} missing -> IDs: {list(missing_ids)[:10]}")
        else:
            print(f"{table.ljust(35)} | ✅ 0 missing")

print("-" * 60)
print(f"Total missing legacy records in PostgreSQL: {missing_records_total}")
