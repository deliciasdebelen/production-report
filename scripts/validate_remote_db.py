import paramiko
import os
import sqlite3
from sqlalchemy import create_engine, text

local_db_path = 'production_remote.db'

print("Downloading production.db via SFTP...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.79', username='administrador', password='GRW7czL3*')

sftp = client.open_sftp()
try:
    sftp.get('/home/administrador/apps/production-report/production.db', local_db_path)
    print("Download complete.")
except Exception as e:
    print("Failed to download:", e)
    exit(1)
sftp.close()
client.close()

print("Connecting to databases...")
sqlite_conn = sqlite3.connect(local_db_path)
sqlite_conn.row_factory = sqlite3.Row

# PostgreSQL is exposed on 5434 on the remote host .79
pg_engine = create_engine("postgresql://app_user:production_password@192.168.1.79:5434/production_db")

cur_sqlite = sqlite_conn.cursor()
cur_sqlite.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != 'alembic_version'")
tables = [row['name'] for row in cur_sqlite.fetchall()]

print(f"{'Table Name'.ljust(35)} | {'SQLite'.ljust(10)} | {'PostgreSQL'.ljust(10)} | {'Diff'.ljust(10)}")
print("-" * 75)

total_diff = 0
missing_tables = []

with pg_engine.connect() as pg_conn:
    for table in tables:
        cur_sqlite.execute(f'SELECT COUNT(*) as c FROM "{table}"')
        sq_count = cur_sqlite.fetchone()['c']
        
        try:
            res = pg_conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).fetchone()
            pg_count = res[0]
        except Exception as e:
            pg_count = "ERROR"
            diff = "N/A"
            mark = "❌"
            missing_tables.append(table)
        else:
            diff = sq_count - pg_count
            mark = "✅" if diff == 0 else "❌"
            if isinstance(diff, int):
                total_diff += abs(diff)
            
        print(f"{table.ljust(35)} | {str(sq_count).ljust(10)} | {str(pg_count).ljust(10)} | {str(diff).ljust(10)} {mark}")
        
print("-" * 75)
print(f"Total discrepancy: {total_diff} records")
if missing_tables:
    print(f"Tables with errors in PostgreSQL: {', '.join(missing_tables)}")

