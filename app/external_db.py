from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import urllib.parse

# Connection string for Profit Plus (SQL Server)
# User provided: 192.168.1.205, PROFIT/profit, db: carmal_a
# Using pyodbc driver (ODBC Driver 17 for SQL Server)

RAW_CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.1.232;"
    "DATABASE=carmal_a;"
    "UID=PROFIT;"
    "PWD=profit;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

params_a = urllib.parse.quote_plus(RAW_CONN_STR)

EXTERNAL_DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={params_a}"

# Manufacturing Engine (carmal_m)
# Replace in the raw string FIRST, then encode
raw_m = RAW_CONN_STR.replace("DATABASE=carmal_a;", "DATABASE=carmal_m;")
params_m = urllib.parse.quote_plus(raw_m)

# Template for URL
DB_URL_TEMPLATE = "mssql+pyodbc:///?odbc_connect={}"

def create_engine_for_db(db_name):
    p_raw = RAW_CONN_STR.replace("DATABASE=carmal_a;", f"DATABASE={db_name};")
    p_enc = urllib.parse.quote_plus(p_raw)
    return create_engine(DB_URL_TEMPLATE.format(p_enc))

# Administrative / Logistics Engine (Default)
engine_a = create_engine(EXTERNAL_DATABASE_URL)
external_engine = engine_a # Alias for compatibility
SessionA = sessionmaker(autocommit=False, autoflush=False, bind=engine_a)

# Manufacturing Engine
engine_m = create_engine(f"mssql+pyodbc:///?odbc_connect={params_m}")
SessionM = sessionmaker(autocommit=False, autoflush=False, bind=engine_m)

def get_external_db():
    db = SessionA()
    try:
        yield db
    finally:
        db.close()

def get_manufacturing_db():
    db = SessionM()
    try:
        yield db
    finally:
        db.close()
