
import os
import shutil

SOURCE = "app/migrate_db.py"
DEST = "migrate_db_local.py"

with open(SOURCE, "r") as f:
    content = f.read()

content = content.replace('/app/production.db', 'production.db')

with open(DEST, "w") as f:
    f.write(content)

print("Created migrate_db_local.py, executing...")
os.system(r".\venv\Scripts\python migrate_db_local.py")
os.remove(DEST)
print("Done.")
