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
        Queries Profit Plus for document totals via SP.
        Returns dict: {'boxes': float}
        """
        try:
            # Determine table based on prefix
            is_nent = "NENT" in doc_ref.upper() or "NOTA" in doc_ref.upper()
            
            # Ref convention: prefix-number (FACT-12345) or prefix:number (FACT:12345)
            clean_ref = doc_ref.split('-')[-1].split(':')[-1].strip()
            
            boxes_sum = 0.0
            
            if is_nent:
                sql = text("EXEC SP_CRM_NotasEntregaPendientesPorClienteV2 @doc_num = :d")
            else:
                # Fallback / Generic Search (Try Invoice first as default)
                sql = text("EXEC SP_CRM_FacturasPendientesPorClienteV2 @doc_num = :d")
                
            result = self.ext_db.execute(sql, {"d": clean_ref}).fetchall()
            
            if not result:
                 # Si no consigue factura, y tampoco se sabia si era nota, intentar como nota como fallback
                 if not is_nent:
                     sql = text("EXEC SP_CRM_NotasEntregaPendientesPorClienteV2 @doc_num = :d")
                     result = self.ext_db.execute(sql, {"d": clean_ref}).fetchall()
                     
            if not result:
                return None
                
            # Summarize boxes from SP result
            for row in result:
                # Depending on SQLAlchemy version, row might be tuple or have _mapping
                row_map = row._mapping if hasattr(row, '_mapping') else row._asdict() if hasattr(row, '_asdict') else dict(row)
                
                raw_boxes = None
                for c in ['Cantidad Cajas', 'cantidad_cajas', 'cajas']:
                    if c in row_map:
                        raw_boxes = row_map[c]
                        break
                    else:
                        for k in row_map.keys():
                            if c.lower() in str(k).lower():
                                raw_boxes = row_map[k]
                                break
                    if raw_boxes is not None: break
                        
                if raw_boxes is not None:
                    try:
                        boxes_sum += float(raw_boxes)
                    except:
                        pass

            return {"boxes": boxes_sum}
            
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

