
import os
import sys
import datetime
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import SessionLocal
from app.models import AuditLog, LogisticsDispatch

def insert_audit_log():
    db = SessionLocal()
    try:
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

        now = datetime.datetime.now()
        
        new_log = AuditLog(
            resource_type="dispatch",
            resource_id=str(dispatch.id),
            discrepancy_type="system_audit_sp",
            severity="medium",
            description="AUDITORÍA INTELIGENTE: Se detectó y corrigió descuadre histórico entre renglones y totales cabecera en BD `carmal_a` (SP `RepFormatoDevolucionClienteOM_Lote` y `repformatofacturaventaOM_consolidada`). División por cero mitigada. Nuevo SP V2 en producción.",
            source_value="Descuadre en Totales / Lotes Ocultos",
            target_value="Totales Conciliados / Lotes Visibles",
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
