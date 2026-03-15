
import sys
import os

# Ensure app is in path if needed (though running from root usually works)
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models import LogisticsDispatch
import datetime

db = SessionLocal()

print(f"--- Diagnostic Run at {datetime.datetime.now()} ---")

print("--- Checking LogisticsDispatch after 2026-02-04 ---")
try:
    # Check explicitly for recent records
    recent = db.query(LogisticsDispatch).filter(LogisticsDispatch.date >= datetime.datetime(2026, 2, 4)).all()
    if not recent:
        print("No LogisticsDispatch records found after 2026-02-04.")
    else:
        for i in recent:
            print(f"ID: {i.id} | Date: {i.date} | Client: {i.client_destination}")
            
    # Also check total count
    cnt = db.query(LogisticsDispatch).count()
    print(f"Total LogisticsDispatch Count: {cnt}")
    
except Exception as e:
    print(f"Error querying: {e}")
except Exception as e:
    print(f"Error querying ProductionReport: {e}")

db.close()
