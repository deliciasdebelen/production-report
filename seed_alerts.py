from app.database import SessionLocal, engine
from app import models
from app.models import LogisticsDispatch, AuditLog
import json
import datetime
import random

# Create tables if not exist
models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

# 1. Create Dispatch for Critical Alert
dispatch1_query = db.query(LogisticsDispatch).filter(LogisticsDispatch.document_ref.like("GUIA-00000035%")).first()
if dispatch1_query:
    print("Dispatch 1 exists. Updating...")
    dispatch1 = dispatch1_query
else:
    dispatch1 = LogisticsDispatch()

dispatch1.document_ref = "GUIA-00000035 | Fact: FACT:0000013572"
dispatch1.client_destination = "SUMINISTROS 1979, C.A."
dispatch1.items_json = json.dumps([
    {"qty": 3564.0, "unit": "UNI", "item": "PIPITA Mayonesa Tradicional PEAD 445g"},
    {"qty": 3156.0, "unit": "UNI", "item": "Las Delicias de Belén Mayonesa Premium Tradicional PET 910g"}
])
dispatch1.date = datetime.datetime.now() # or specific date
db.add(dispatch1)
db.commit()
db.refresh(dispatch1)

# Create AuditLog for Dispatch 1
log1 = db.query(AuditLog).filter(AuditLog.resource_id == str(dispatch1.id), AuditLog.severity == 'critical').first()
if not log1:
    log1 = AuditLog(
        resource_type='dispatch',
        resource_id=str(dispatch1.id),
        discrepancy_type='weight_mismatch',
        severity='critical',
        description='Discrepancia crítica en peso calculado vs real. Peso esperado: 1.5kg, Detectado: 1.2kg en lote A123.',
        status='Open'
    )
    db.add(log1)

# 2. Create Dispatch for AI OK
dispatch2_query = db.query(LogisticsDispatch).filter(LogisticsDispatch.document_ref.like("GUIA-00000034%")).first()
if dispatch2_query:
    print("Dispatch 2 exists. Updating...")
    dispatch2 = dispatch2_query
else:
    dispatch2 = LogisticsDispatch()

dispatch2.document_ref = "GUIA-00000034 | Fact: FACT:0000013547,NOTA:0000001406"
dispatch2.client_destination = "Multi-Destino"
dispatch2.items_json = json.dumps([
    {"qty": 12.0, "unit": "UNI", "item": "PIPITA Mayonesa Tradicional PEAD 3.3 kg"},
    {"qty": 12.0, "unit": "UNI", "item": "Delicias de Belén Mermelada Varietal Parchita 250g"},
    {"qty": 120.0, "unit": "UNI", "item": "Las Delicias de Belén Mayonesa Premium Tradicional..."}
])
dispatch2.date = datetime.datetime.now() - datetime.timedelta(days=1)
db.add(dispatch2)
db.commit()
db.refresh(dispatch2)

# Create AuditLog for Dispatch 2 (OK/Low Severity or just Log success?)
# If OK, severity might be low, status Resolved or Open (informational).
log2 = db.query(AuditLog).filter(AuditLog.resource_id == str(dispatch2.id), AuditLog.severity == 'low').first()
if not log2:
    log2 = AuditLog(
        resource_type='dispatch',
        resource_id=str(dispatch2.id),
        discrepancy_type='check',
        severity='low', # AI OK
        description='Validación completada sin errores. Pesos y cantidades coinciden con el estándar.',
        status='Resolved' # Or Open for informational
    )
    db.add(log2)

db.commit()
print("Seeded alerts successfully.")
