import os
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 1. Connect to PostgreSQL (App DB)
PG_URL = "postgresql://app_user:production_password@192.168.1.79:5434/production_db"
pg_engine = create_engine(PG_URL)
with pg_engine.connect() as conn:
    dispatches = conn.execute(text("SELECT id, document_ref, items_json FROM logistics_dispatch WHERE is_annulled = false")).fetchall()

# 2. Connect to SQL Server (Profit Plus - 192.168.1.205)
PROFIT_URL = (
    "mssql+pyodbc:///?odbc_connect="
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.1.205;"
    "DATABASE=carmal_a;"
    "UID=PROFIT;"
    "PWD=profit;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)
profit_engine = create_engine(PROFIT_URL)

mismatches = []

with profit_engine.connect() as profit_conn:
    for dispatch in dispatches:
        dispatch_id = dispatch[0]
        doc_refs_str = dispatch[1] # e.g. "FACT-0000014764, NENT-000000573"
        items_json_str = dispatch[2]
        
        try:
            dispatch_items = json.loads(items_json_str)
        except:
            continue
            
        # We need to aggregate what Profit says for these items across all document refs in this dispatch
        # Actually in logistics_dispatch, is there a 1-to-1 mapping of items to doc_ref in the JSON?
        # Let's just pull and print the JSON first to see the structure of a mismatched one.
        pass

print(f"Total dispatches to check: {len(dispatches)}")
if len(dispatches) > 0:
    print("Sample JSON:", dispatches[-1][2])
