import os
import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# PostgreSQL connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://app_user:production_password@production-report-db:5432/production_db")
pg_engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)

# SQL Server connection (Profit Plus)
SQLSRV_HOST = os.getenv("SQLSRV_HOST", "192.168.1.205")
SQLSRV_DATABASE = os.getenv("SQLSRV_DATABASE", "carmal_a")
SQLSRV_USER = os.getenv("SQLSRV_USER", "PROFIT")
SQLSRV_PASSWORD = os.getenv("SQLSRV_PASSWORD", "profit")

RAW_CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={SQLSRV_HOST};"
    f"DATABASE={SQLSRV_DATABASE};"
    f"UID={SQLSRV_USER};"
    f"PWD={SQLSRV_PASSWORD};"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

params_a = urllib.parse.quote_plus(RAW_CONN_STR)
sqlsrv_engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params_a}")
