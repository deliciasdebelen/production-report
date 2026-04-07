import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models import LogisticsDispatch

db = SessionLocal()

# Find an active dispatch
active_dispatch = db.query(LogisticsDispatch).filter(LogisticsDispatch.status != 'Anulada').first()
if active_dispatch:
    print(f"Active Dispatch ID: {active_dispatch.id}, Status: {active_dispatch.status}, Ref: {active_dispatch.document_ref}")
    
    # Try to annul it to see if it works
    print("Anulling dispatch...")
    active_dispatch.status = 'Anulada'
    db.commit()
    
    # Verify it became annulled
    annulled_dispatch = db.query(LogisticsDispatch).filter(LogisticsDispatch.id == active_dispatch.id).first()
    print(f"Verified Annulled: {annulled_dispatch.status == 'Anulada'} (Status: {annulled_dispatch.status})")
    
    # Restore it back to Active so we don't accidentally ruin production data for a real guide
    print("Restoring dispatch...")
    annulled_dispatch.status = 'Activa'
    db.commit()
    print("Restored.")
else:
    print("No active dispatches found to test.")

db.close()
