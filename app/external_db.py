from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import urllib.parse

# Connection string for Profit Plus (SQL Server)
# User provided: 192.168.1.205, PROFIT/profit, db: carmal_a
# Using pyodbc driver (ODBC Driver 17 for SQL Server)

params = urllib.parse.quote_plus(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.1.205;"
    "DATABASE=carmal_a;"
    "UID=PROFIT;"
    "PWD=profit;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

EXTERNAL_DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={params}"

external_engine = create_engine(EXTERNAL_DATABASE_URL)
ExternalSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=external_engine)

def get_external_db():
    db = ExternalSessionLocal()
    try:
        yield db
    finally:
        db.close()
