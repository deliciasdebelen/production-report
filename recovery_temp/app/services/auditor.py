from sqlalchemy.orm import Session
from sqlalchemy import text
from .. import models
from ..external_db import get_external_db, SessionA
from ..database import SessionLocal
import json

def audit_dispatch_task(dispatch_id: int):
    """
    Background task wrapper for AuditService.
    Creates fresh sessions to avoid closed session errors.
    """
    db = SessionLocal()
    ext_db = SessionA()
    try:
        service = AuditService(db, ext_db)
        service.validate_dispatch(dispatch_id)
    except Exception as e:
        print(f"Audit Task Failed: {e}")
    finally:
        db.close()
        ext_db.close()

class AuditService:
    def __init__(self, db: Session, external_session: Session = None):
        self.db = db
        # If external session not provided, we might need to handle it. 
        # For now assume dependency injection passes it or we create one-off.
        # Ideally, we pass it in.
        self.ext_db = external_session 

    def validate_dispatch(self, dispatch_id: int):
        """
        Validates a specific dispatch against the source documents (Invoices/Notes)
        in the external system (Profit Plus).
        """
        dispatch = self.db.query(models.LogisticsDispatch).filter(models.LogisticsDispatch.id == dispatch_id).first()
        if not dispatch:
            return {"status": "error", "message": "Dispatch not found"}

        # Parse items to get source references
        # Expected format: [{"fact": "FACT-123", "qty": 10, ...}, ...]
        try:
            items = json.loads(dispatch.items_json)
        except:
            return {"status": "error", "message": "Invalid JSON items"}

        discrepancies = []
        
        # Group local totals by Document
        # Map: {"FACT-123": {"boxes": 10, "units": 500}}
        local_docs = {}
        for item in items:
            ref = item.get('fact', 'UNKNOWN').strip().upper()
            if ref == 'UNKNOWN': continue
            
            if ref not in local_docs: local_docs[ref] = {"boxes": 0.0, "units": 0.0}
            
            try: local_docs[ref]["boxes"] += float(item.get('total_cajas', 0))
            except: pass
            
            try: local_docs[ref]["units"] += float(item.get('qty', 0))
            except: pass


        # Verify against External DB
        if not self.ext_db:
             return {"status": "skipped", "message": "No external DB connection"}

        for doc_ref, metrics in local_docs.items():
            # Determine type
            is_invoice = "FACT" in doc_ref or "GUIA" in doc_ref # Simple heuristic
            
            # Fetch Source Data
            # Assume query returns total boxes/units for that document
            # This query depends on specific Profit Plus schema (saFacturaVenta vs saNotaEntregaVenta)
            # Using a generic wrapper query logic here.
            
            source_data = self._fetch_external_totals(doc_ref)
            
            if not source_data:
                self._log_issue(dispatch.id, doc_ref, "missing_source", "high", "Documento no encontrado en Profit")
                continue

            # Compare Boxes (Tolerance 0.1)
            diff_boxes = abs(metrics['boxes'] - source_data['boxes'])
            if diff_boxes > 0.1:
                self._log_issue(
                    dispatch.id, doc_ref, "box_mismatch", "medium", 
                    f"Diferencia en Cajas: Local={metrics['boxes']} vs Profit={source_data['boxes']}",
                    metrics['boxes'], source_data['boxes']
                )

    def _fetch_external_totals(self, doc_ref: str):
        """
        Queries Profit Plus for document totals.
        Returns dict: {'boxes': float}
        """
        # Determine table based on prefix or generic search
        # Ref convention: prefix-number (FACT-2233)
        
        try:
            # Query simplified for saFacturaVenta
            # We need to strip prefix for number sometimes, depends on Profit setup.
            # Assuming Profit stores 'doc_num' matching the suffix number usually.
            
            # Using LIKE to find doc
            # TODO: Refine this query with actual schema knowledge from previous tasks
            # Schema: saFacturaVenta (co_tipo_doc, nro_doc) 
            # We will try exact match on nro_doc if we strip prefix, or full string.
            
            # Determine table based on prefix
            is_nent = "NENT" in doc_ref.upper()
            is_fact = "FACT" in doc_ref.upper()
            
            clean_ref = doc_ref.split('-')[-1].strip() # 12345
            
            # Logic: Explicit Routing
            if is_nent:
                sql = text(f"""
                    SELECT SUM(total_bultos) as boxes
                    FROM saNotaEntregaVenta
                    WHERE nro_doc LIKE '%{clean_ref}'
                """)
                result = self.ext_db.execute(sql).fetchone()
                if result and result[0] is not None:
                     return {"boxes": float(result[0])}
            
            elif is_fact:
                sql = text(f"""
                    SELECT SUM(total_bultos) as boxes
                    FROM saFacturaVenta
                    WHERE nro_doc LIKE '%{clean_ref}'
                """)
                result = self.ext_db.execute(sql).fetchone()
                if result and result[0] is not None:
                     return {"boxes": float(result[0])}
            
            else:
                # Fallback / Generic Search (Try Invoice first as default)
                sql_fact = text(f"""
                    SELECT SUM(total_bultos) as boxes
                    FROM saFacturaVenta
                    WHERE nro_doc LIKE '%{clean_ref}'
                """)
                result = self.ext_db.execute(sql_fact).fetchone()
                if result and result[0] is not None:
                     return {"boxes": float(result[0])}
                     
                # Try Note
                sql_nent = text(f"""
                    SELECT SUM(total_bultos) as boxes
                    FROM saNotaEntregaVenta
                    WHERE nro_doc LIKE '%{clean_ref}'
                """)
                result_nent = self.ext_db.execute(sql_nent).fetchone()
                if result_nent and result_nent[0] is not None:
                     return {"boxes": float(result_nent[0])}
            
            return None
            
        except Exception as e:
            print(f"External Query Error: {e}")
            return None

    def _log_issue(self, dispatch_id, doc_ref, type_code, severity, desc, val_src=None, val_tgt=None):
        # Check if already exists to avoid dupes?
        exists = self.db.query(models.AuditLog).filter(
            models.AuditLog.resource_id == str(dispatch_id),
            models.AuditLog.discrepancy_type == type_code,
            models.AuditLog.description.like(f"%{doc_ref}%")
        ).first()
        
        if not exists:
            log = models.AuditLog(
                resource_type="dispatch",
                resource_id=str(dispatch_id),
                discrepancy_type=type_code,
                severity=severity,
                description=desc,
                source_value=str(val_src) if val_src else None,
                target_value=str(val_tgt) if val_tgt else None
            )
            self.db.add(log)
            self.db.commit()

