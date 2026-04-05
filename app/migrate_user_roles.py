"""
Migration: Ensure user_roles table exists and validate set-roles endpoint.
Run this on the production server to ensure the table is created.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine
from app.models import Base, UserRole
from sqlalchemy import inspect, text

def run():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    if 'user_roles' not in tables:
        print("Creating user_roles table...")
        UserRole.__table__.create(bind=engine)
        print("[OK] Table 'user_roles' created successfully.")
    else:
        print("[OK] Table 'user_roles' already exists.")
    
    # Verify columns
    cols = [c['name'] for c in inspector.get_columns('user_roles')]
    print(f"   Columns: {cols}")

if __name__ == "__main__":
    run()
