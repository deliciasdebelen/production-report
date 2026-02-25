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

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    permissions = Column(Text, default="{}") # JSON: {"module": ["read", "write"]}
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(Integer, ForeignKey("roles.id"), default=1) # 1=KPI, 2=Prod, 3=Plan, 4=Admin, 5=Almacen, 6=Inventory, 7=Patrimonial
    is_active = Column(Integer, default=1)
    
    role_obj = relationship("Role")

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

# --- INTELLIGENCE / AUDIT MODELS ---

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    resource_type = Column(String, index=True) # e.g., "dispatch", "production"
    resource_id = Column(String, index=True)   # ID of the record
    discrepancy_type = Column(String)          # e.g., "weight_mismatch", "box_count_mismatch"
    severity = Column(String)                  # "low", "medium", "high", "critical"
    description = Column(Text)                 # Human readable detail
    
    source_value = Column(String, nullable=True) # Value from Source (Profit Plus)
    target_value = Column(String, nullable=True) # Value from Target (App)
    
    status = Column(String, default="Open")    # Open, Investigate, Resolved, Ignored
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SystemInsight(Base):
    __tablename__ = "system_insights"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, index=True) # "optimization", "pattern", "anomaly"
    insight_key = Column(String, unique=True, index=True) # unique identifier for the insight
    description = Column(Text)
    
    # Validation Data
    occurrence_count = Column(Integer, default=1)
    confidence_score = Column(Float, default=0.0) # 0.0 to 1.0 (AI confidence)
    
    last_detected = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- SUPPORT MODULE MODELS ---

class SupportDepartment(Base):
    __tablename__ = "support_departments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    
class SupportStatus(Base):
    __tablename__ = "support_status"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    color_hex = Column(String, default="#808080")
    
class SupportPriority(Base):
    __tablename__ = "support_priorities"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    level = Column(Integer, default=1) # 1=Low, 4=Urgent

class SupportType(Base):
    __tablename__ = "support_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

class SupportTicket(Base):
    __tablename__ = "support_tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False) # e.g., SOP-2024-001
    
    description = Column(Text, nullable=False)
    attachment_url = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    
    # Foreign Keys
    created_by_id = Column(Integer, ForeignKey("users.id"))
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    department_id = Column(Integer, ForeignKey("support_departments.id"), nullable=True)
    type_id = Column(Integer, ForeignKey("support_types.id"), nullable=True)
    priority_id = Column(Integer, ForeignKey("support_priorities.id"), nullable=True)
    status_id = Column(Integer, ForeignKey("support_status.id"), nullable=True)
    
    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    department = relationship("SupportDepartment")
    support_type = relationship("SupportType")
    priority = relationship("SupportPriority")
    status = relationship("SupportStatus")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)

# --- AI PARAMETERS MODULE ---

class AIFunctionality(Base):
    __tablename__ = "ai_functionalities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    parameters = relationship("AIParameter", back_populates="functionality")

class AIParameter(Base):
    __tablename__ = "ai_parameters"

    id = Column(Integer, primary_key=True, index=True)
    functionality_id = Column(Integer, ForeignKey("ai_functionalities.id"), nullable=False)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False) # Stored as string, cast as needed
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    functionality = relationship("AIFunctionality", back_populates="parameters")


# --- TELEGRAM NOTIFICATION SUBSCRIBERS ---

class TelegramSubscriber(Base):
    __tablename__ = "telegram_subscribers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)            # Nombre descriptivo
    chat_id = Column(String, nullable=False)          # Número o chat_id de Telegram
    report_type = Column(String, default="MP")        # MP, Stock, General
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
