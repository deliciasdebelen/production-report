import os
import sys

db_file = 'app/database.py'
with open(db_file, 'r') as f:
    content = f.read()

# Change the strict condition that forces postgres
modified = content.replace('if not _db_url or "sqlite" in _db_url:', 'if not _db_url:')

with open(db_file, 'w') as f:
    f.write(modified)

print("database.py temporarily patched to allow sqlite.")
