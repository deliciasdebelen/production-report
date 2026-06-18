import datetime
import json
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://openpg:openpgpwd@localhost:5432/production_db"
engine = create_engine(DATABASE_URL)

def insert_audit_log():
    try:
        with engine.begin() as conn:
            # First fetch a valid dispatch ID without using models
            result = conn.execute(text("SELECT id FROM logistics_dispatch ORDER BY id DESC LIMIT 1"))
            dispatch_id = result.scalar()
            
            if not dispatch_id:
                print("No dispatch found, creating a dummy one...")
                insert_dispatch = text("""
                    INSERT INTO logistics_dispatch (client_destination, document_ref, items_json, date) 
                    VALUES (:client, :doc_ref, :items, :date) RETURNING id
                """)
                dispatch_id = conn.execute(insert_dispatch, {
                    "client": "System Generated (Audit Test)", 
                    "doc_ref": "SISTEMA|AUDITORIA", 
                    "items": json.dumps([{"item": "Audit System Alert", "qty": 1, "unit": "SYS"}]),
                    "date": datetime.datetime.now()
                }).scalar()
            
            # Now insert the audit log directly using raw SQL
            now = datetime.datetime.now()
            insert_log = text("""
                INSERT INTO audit_logs (
                    resource_type, resource_id, discrepancy_type, severity, description, 
                    source_value, target_value, status, created_at
                ) VALUES (
                    :res_type, :res_id, :disc_type, :severity, :desc, 
                    :src_val, :tgt_val, :status, :created_at
                ) RETURNING id
            """)
            
            new_log_id = conn.execute(insert_log, {
                "res_type": "dispatch",
                "res_id": str(dispatch_id),
                "disc_type": "system_audit_sp",
                "severity": "medium",
                "desc": "AUDITORÍA INTELIGENTE: Se detectó descuadre histórico entre renglones y totales de cabecera en la BD `carmal_a` (SP `RepFormatoDevolucionClienteOM_Lote` y `repformatofacturaventaOM_consolidada`). Lotes invisibles y división por cero mitigada.",
                "src_val": "Totales Descuadrados / Sin Lote",
                "tgt_val": "Cuadre Perfecto / Lotes Integrados V2",
                "status": "WARNING",
                "created_at": now
            }).scalar()
            
            print(f"✅ AuditLog successfully added! ID: {new_log_id} attached to dispatch {dispatch_id}")
            
    except Exception as e:
        print(f"Error inserting audit log: {e}")

if __name__ == "__main__":
    insert_audit_log()
