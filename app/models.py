from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from .database import Base
import uuid
import datetime

def generate_id():
    # Random ID + Current Date (YYYYMMDD)
    date_str = datetime.date.today().strftime("%Y%m%d")
    random_str = str(uuid.uuid4())[:8]
    return f"{date_str}-{random_str}"

class ProductionReport(Base):
    __tablename__ = "production_reports"

    id = Column(String, primary_key=True, index=True, default=generate_id)
    batch_qty = Column(Integer, nullable=False)
    article_type = Column(String, nullable=False)
    kg_produced = Column(Float, nullable=False)
    presentation = Column(String, nullable=False)
    boxes = Column(Float, default=0.0)

    # PT (Producto Terminado)
    pt_units = Column(Integer, default=0)
    pt_lab = Column(Integer, default=0)
    pt_burned = Column(Integer, default=0)

    # MP (Materia Prima)
    mp_caps_clean = Column(Integer, default=0)
    mp_caps_dirty = Column(Integer, default=0)
    mp_waste_kg = Column(Float, default=0.0)
    mp_waste_image = Column(String, nullable=True)

    # New Logistics Fields
    order_number = Column(String, unique=True, index=True, nullable=True) # 10-digit sequential
    status = Column(String, default="Pending") # Pending, Confirmed
    planning_order_ids = Column(Text, nullable=True) # "1, 2, 3"

    # Consumo Rapido
    cons_type = Column(String, nullable=True)
    cons_count = Column(Float, default=0.0)
    cons_unit_weight = Column(Float, default=0.0)
    cons_qty = Column(Float, default=0.0)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    inserted_at = Column(DateTime(timezone=True), server_default=func.now())

class ProductionPlanning(Base):
    __tablename__ = "production_planning"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, unique=True, index=True, nullable=True) # 10-digit sequential
    date = Column(String, nullable=False) # Storing as YYYY-MM-DD
    article = Column(String, nullable=False)
    presentation = Column(String, nullable=False)
    batches = Column(Integer, default=0)
    kg = Column(Float, default=0.0)
    units = Column(Integer, default=0)
    boxes = Column(Float, default=0.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(Integer, default=1) # 1=KPI, 2=Prod, 3=Plan, 4=Admin
    is_active = Column(Integer, default=1)

class LogisticsReceptionProduction(Base):
    __tablename__ = "logistics_reception_production"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    production_report_id = Column(String, nullable=True) 
    product_name = Column(String, nullable=False)
    quantity = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class LogisticsReceptionMerchandise(Base):
    __tablename__ = "logistics_reception_merchandise"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    supplier = Column(String, nullable=False)
    document_ref = Column(String, nullable=True) # Boleta/Factura
    items_json = Column(Text, nullable=False) # JSON format: [{"item": "X", "qty": 10}, ...]
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class LogisticsDispatch(Base):
    __tablename__ = "logistics_dispatch"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    client_destination = Column(String, nullable=False)
    document_ref = Column(String, nullable=True)
    items_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
