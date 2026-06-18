import sys
import os

# Ensure app is in path - go up one level from scripts/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import engine
from app.models import Base
from sqlalchemy import text

def run_migration():
    print("Creating all missing tables (e.g., email_logs)...")
    Base.metadata.create_all(bind=engine)
    
    # Check what dialect we are using
    dialect = engine.dialect.name
    print(f"Using dialect: {dialect}")

    with engine.connect() as conn:
        try:
            if dialect == 'sqlite':
                conn.execute(text('ALTER TABLE support_settings ADD COLUMN smtp_server VARCHAR DEFAULT "smtp.gmail.com"'))
                conn.execute(text('ALTER TABLE support_settings ADD COLUMN smtp_port INTEGER DEFAULT 587'))
                conn.execute(text('ALTER TABLE support_settings ADD COLUMN smtp_user VARCHAR DEFAULT ""'))
                conn.execute(text('ALTER TABLE support_settings ADD COLUMN smtp_password VARCHAR DEFAULT ""'))
            elif dialect == 'postgresql':
                conn.execute(text('ALTER TABLE support_settings ADD COLUMN IF NOT EXISTS smtp_server VARCHAR DEFAULT \'smtp.gmail.com\''))
                conn.execute(text('ALTER TABLE support_settings ADD COLUMN IF NOT EXISTS smtp_port INTEGER DEFAULT 587'))
                conn.execute(text('ALTER TABLE support_settings ADD COLUMN IF NOT EXISTS smtp_user VARCHAR DEFAULT \'\''))
                conn.execute(text('ALTER TABLE support_settings ADD COLUMN IF NOT EXISTS smtp_password VARCHAR DEFAULT \'\''))
            print("Successfully added columns to support_settings.")
        except Exception as e:
            print(f"Error altering table (columns might already exist): {e}")

        conn.commit()

if __name__ == "__main__":
    run_migration()
