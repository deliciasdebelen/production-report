import paramiko
import os
import sqlite3

local_db_path = 'production_remote_193.db'

print("Downloading data/production.db from 192.168.1.193 via SFTP...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.193', username='administrador', password='GRW7czL3*')

sftp = client.open_sftp()
try:
    sftp.get('/home/administrador/production-report/data/production.db', local_db_path)
    print("Download complete.")
except Exception as e:
    print("Failed to download data/production.db:", e)
    try:
        sftp.get('/home/administrador/production-report/production.db', local_db_path)
        print("Downloaded root production.db instead.")
    except Exception as e2:
         print("Also failed to download root:", e2)
         sftp.close()
         client.close()
         exit(1)

sftp.close()
client.close()

print("Connecting to local SQLite DB copy from 193...")
sqlite_conn = sqlite3.connect(local_db_path)
c = sqlite_conn.cursor()

try:
    count = c.execute("SELECT COUNT(*) FROM production_planning").fetchone()[0]
    dates = c.execute("SELECT MIN(date), MAX(date) FROM production_planning").fetchone()
    print(f"Planning 193 count: {count} | Dates: {dates}")
except Exception as e:
    print("Error querying planning:", e)

try:
    count_prod = c.execute("SELECT COUNT(*) FROM logistics_reception_production").fetchone()[0]
    print(f"Production 193 count: {count_prod}")
except Exception as e:
    print("Error querying production:", e)
