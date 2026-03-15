import os
from sqlalchemy import create_engine, text

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("No DATABASE_URL found. Check environment vars.")
    exit(1)

print(f"Connecting to {db_url}...")
engine = create_engine(db_url)

try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE logistics_dispatch ADD COLUMN is_annulled BOOLEAN DEFAULT FALSE;"))
        print("Successfully added is_annulled to logistics_dispatch.")
except Exception as e:
    print(f"Migration error: {e}")
