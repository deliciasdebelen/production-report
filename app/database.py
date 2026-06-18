from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os

# Use environment variable if set, otherwise definitively fallback to PostgreSQL
# to ensure no SQLite instances are ever recreated.
_db_url = os.getenv("DATABASE_URL", "")

if os.getenv("TESTING") == "1":
    SQLALCHEMY_DATABASE_URL = _db_url or "sqlite:///./test.db"
elif not _db_url or "sqlite" in _db_url:
    # Ensure no local SQLite instances are recreated in production
    SQLALCHEMY_DATABASE_URL = "postgresql://app_user:production_password@production_report_db:5432/production_db"
else:
    SQLALCHEMY_DATABASE_URL = _db_url

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
