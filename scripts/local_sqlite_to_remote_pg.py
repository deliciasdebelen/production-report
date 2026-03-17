import subprocess
import os

print("1. Generating SQLite dump locally...")
# Dump the patched live SQLite file
subprocess.run("sqlite3 production.db.live '.dump' > dump.sql", shell=True, check=True)

print("2. Filtering SQLite specific syntax...")
# Clean the dump using grep equivalent in python to ensure it works on Windows
with open("dump.sql", "r", encoding="utf-8") as f_in, open("data_only.sql", "w", encoding="utf-8") as f_out:
    for line in f_in:
        idx_line = line.strip()
        if not idx_line.startswith("PRAGMA") and \
           not idx_line.startswith("BEGIN") and \
           not idx_line.startswith("COMMIT") and \
           not idx_line.startswith("CREATE") and \
           "DELETE FROM sqlite_sequence" not in idx_line and \
           "sqlite_sequence" not in idx_line:
            f_out.write(line)

print("3. Importing cleaned SQL data into the remote Production PostgreSQL container...")
pg_url = "postgresql://app_user:production_password@192.168.1.79:5434/production_db"
os.environ["PGPASSWORD"] = "production_password"

# Use local psql to push the data_only.sql into the remote DB
try:
    subprocess.run([
        "psql", "-h", "192.168.1.79", "-p", "5434", "-U", "app_user", "-d", "production_db", "-f", "data_only.sql"
    ], check=True)
    print("SQL import completed successfully!")
except subprocess.CalledProcessError as e:
    print(f"PSQL import failed with code: {e.returncode}")
except FileNotFoundError:
    print("psql is not installed locally. Can't run direct import.")
