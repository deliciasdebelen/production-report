import subprocess

# Local path to the patched production DB
sqlite_path = "production.db.live"

# We exposed 5434 in docker-compose.yml on the .79 host, so we connect via the host IP and that port
pg_url = "postgresql://app_user:production_password@192.168.1.79:5434/production_db"

print(f"Starting migration from {sqlite_path} to {pg_url}...")

# Call the standalone migration script locally to push data to the remote PG database
try:
    subprocess.run([
        "python", "scripts/migrate_sqlite_to_pg_standalone.py",
        "--sqlite", sqlite_path,
        "--pg", pg_url
    ], check=True)
    print("Migration completed successfully!")
except subprocess.CalledProcessError as e:
    print(f"Migration failed with exit code: {e.returncode}")
except Exception as e:
    print(f"Migration error: {e}")
