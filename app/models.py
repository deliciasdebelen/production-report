from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, func, Boolean
from sqlalchemy.orm import relationship
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
    mp_containers = Column(Integer, default=0)
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
    color = Column(String, default="#3b82f6")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

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
    units_pending = Column(Integer, nullable=True) # Tracks countdown
    boxes = Column(Float, default=0.0)
    waste_percentage = Column(Float, default=0.0)
    waste_kg = Column(Float, default=0.0)
    status = Column(String, default="Pending") # Pending, Processed
    notes = Column(Text, nullable=True)
    color = Column(String, default="#3b82f6")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

class InventoryCapture(Base):
    __tablename__ = "inventory_captures"

    id = Column(Integer, primary_key=True, index=True)
    capture_type = Column(String, nullable=False) # 'Inicio' or 'Cierre'
    article_code = Column(String, nullable=False)
    article_description = Column(String, nullable=False)
    batch = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    capture_date = Column(String, nullable=False) # YYYY-MM-DD
    capture_time = Column(String, nullable=False) # HH:MM
    department = Column(String, nullable=True) # Logistica/Produccion
    out_of_range = Column(Boolean, default=False)
    
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(Integer, default=1) # 1=KPI, 2=Prod, 3=Plan, 4=Admin, 5=Almacen, 6=Inventory, 7=Patrimonial
    is_active = Column(Integer, default=1)

class LogisticsReceptionProduction(Base):
    __tablename__ = "logistics_reception_production"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    production_report_id = Column(String, nullable=True) 
    product_name = Column(String, nullable=False)
    quantity = Column(Float, default=0.0)
    status = Column(String, default="Recepcionado")
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
    
    route_id = Column(Integer, ForeignKey("logistics_routes.id"), nullable=True)
    route = relationship("LogisticsRoute")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Channel(Base):
    __tablename__ = 'channels'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, default='channel') # channel, chat
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, index=True)
    body = Column(Text, nullable=False)
    message_type = Column(String, default='comment') # notification, comment, email
    author_id = Column(Integer, ForeignKey('users.id'), nullable=True) # System messages might be null
    channel_id = Column(Integer, ForeignKey('channels.id'), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    author = relationship('User')
    channel = relationship('Channel')


class InventoryCaptureHeader(Base):
    __tablename__ = "inventory_headers"

    id = Column(Integer, primary_key=True, index=True)
    correlative = Column(String, unique=True, index=True, nullable=False) # Generated ID
    date = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="Confirmed")
    notes = Column(Text, nullable=True)

    user = relationship("User")
    lines = relationship("InventoryCaptureLine", back_populates="header")

class InventoryCaptureLine(Base):
    __tablename__ = "inventory_lines"

    id = Column(Integer, primary_key=True, index=True)
    header_id = Column(Integer, ForeignKey("inventory_headers.id"))
    article_code = Column(String, nullable=False)
    article_description = Column(String, nullable=False)
    batch = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    
    header = relationship("InventoryCaptureHeader", back_populates="lines")

class MessageStatus(Base):
    __tablename__ = 'message_statuses'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    message_id = Column(Integer, ForeignKey('messages.id'), index=True)

class LogisticsRoute(Base):
    __tablename__ = "logistics_routes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class NotificationSubscriber(Base):
    __tablename__ = 'notification_subscribers'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    report_type = Column(String, default='Inventory') # Inventory, etc.
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
