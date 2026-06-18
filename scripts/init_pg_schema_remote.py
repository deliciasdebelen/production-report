import sqlalchemy
from app.database import Base
from app import models

# PG connection string for the container on .79
pg_url = "postgresql://app_user:production_password@192.168.1.79:5434/production_db"

print(f"Connecting to {pg_url} to create schema...")
try:
    engine = sqlalchemy.create_engine(pg_url)
    Base.metadata.create_all(bind=engine)
    print("Schema creation successful!")
except Exception as e:
    print(f"Error creating schema: {e}")
