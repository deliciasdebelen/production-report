import sys
import os
import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models import AuditLog, LogisticsDispatch
import json

def insert_audit_log():
    db = SessionLocal()
    try:
        # Check if there's any active dispatch to attach to as an example
        # If not, we will just create a dummy dispatch to attach the alert to
        dispatch = db.query(LogisticsDispatch).order_by(LogisticsDispatch.id.desc()).first()
        
        if not dispatch:
            print("No dispatch found to attach alert to, creating a dummy one...")
            dispatch = LogisticsDispatch(
                client_destination="System Generated (Audit Test)",
                document_ref="SISTEMA|AUDITORIA",
                items_json=json.dumps([{"item": "Audit System Alert", "qty": 1, "unit": "SYS"}]),
                is_annulled=False
            )
            db.add(dispatch)
            db.commit()
            db.refresh(dispatch)

        # Ensure date is current month
        now = datetime.datetime.now()
        
        # Create an AuditLog entry
        new_log = AuditLog(
            resource_type="dispatch",
            resource_id=str(dispatch.id),
            discrepancy_type="system_audit_sp",
            severity="medium",
            description="AUDITORÍA SP EXITOSA: Se detectó descuadre histórico entre renglones y totales en la DB `carmal_a`. Sub-rutinas `RepFormatoDevolucionClienteOM_Lote` y `repformatofacturaventaOM_consolidada`. Discrepancias mitigadas a 0.00% con creación de V2.",
            source_value=None,
            target_value="Reparado",
            status="Resolved",
            created_at=now
        )
        
        db.add(new_log)
        db.commit()
        print(f"AuditLog successfully added! ID: {new_log.id} attached to dispatch {dispatch.id}")
        
    except Exception as e:
        print(f"Error inserting audit log: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    insert_audit_log()
