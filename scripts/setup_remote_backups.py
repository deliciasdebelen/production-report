import paramiko
import sys

# Configuration
HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22
REMOTE_APP_DIR = "/home/administrador/apps/production-report"
BACKUP_DIR = "/home/administrador/backups/production-report"

# Shell script content to be created on server
BACKUP_SCRIPT_CONTENT = f"""#!/bin/bash
# Database Backup Script
# Created by Auto-Setup

BACKUP_DIR="{BACKUP_DIR}"
APP_DIR="{REMOTE_APP_DIR}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_FILE="production.db"
BACKUP_FILE="$BACKUP_DIR/production.db_$TIMESTAMP.bak"

# Create backup directory if not exists
mkdir -p "$BACKUP_DIR"

# Copy database
# We copy even if running (SQLite wal mode usually handles reads fine, 
# but for perfect consistency one might use sqlite3 .backup command if installed.
# For now, simple copy is standard for this setup).
cp "$APP_DIR/$DB_FILE" "$BACKUP_FILE"

# Keep only last 30 backups
ls -dt "$BACKUP_DIR"/* | tail -n +31 | xargs -r rm

echo "Backup created: $BACKUP_FILE"
"""

def setup_backups():
    print(f"Setting up backups on {HOSTNAME}...")

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)

        # 1. Create Directories and Script
        sftp = client.open_sftp()
        
        # Create script file locally then upload
        local_script = "temp_backup_script.sh"
        with open(local_script, "w", newline='\n') as f:

            f.write(BACKUP_SCRIPT_CONTENT)
            
        remote_script_path = f"/home/{USERNAME}/backup_production_db.sh"
        print(f"Uploading backup script to {remote_script_path}...")
        sftp.put(local_script, remote_script_path)
        sftp.close()
        
        # Make executable and create folder
        client.exec_command(f"chmod +x {remote_script_path}")
        client.exec_command(f"mkdir -p {BACKUP_DIR}")

        # 2. Configure Cron
        print("Configuring Cron Job (Daily at 03:00 AM)...")
        
        # Check if job exists
        stdin, stdout, stderr = client.exec_command("crontab -l")
        current_cron = stdout.read().decode().strip()
        
        cron_job = f"0 3 * * * {remote_script_path} >> /home/{USERNAME}/backup.log 2>&1"
        
        if cron_job in current_cron:
            print("Cron job already exists. Skipping.")
        else:
            # Append new job
            new_cron = f"{current_cron}\n{cron_job}\n"
            # Write back
            # Be careful with echo and newlines, easiest is to echo into a tmp file and load
            cmd = f'echo "{new_cron}" | crontab -'
            stdin, stdout, stderr = client.exec_command(cmd)
            if stderr.read():
                print("Warning writing cron:")
                print(stderr.read().decode())
            else:
                print("Cron job added successfully.")

        client.close()
        
        import os
        if os.path.exists(local_script):
            os.remove(local_script)
            
        print(f"\nBackup setup complete!")
        print(f"Backups will be stored in: {BACKUP_DIR}")

    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_backups()
