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
    role = Column(Integer, ForeignKey("roles.id"), default=1) # 1=KPI, 2=Prod, 3=Plan, 4=Admin, 5=Almacen, 6=Inventory, 7=Patrimonial, 8=Director
    is_active = Column(Integer, default=1)
    
    role_obj = relationship("Role", foreign_keys=[role])
    extra_roles = relationship("UserRole", back_populates="user")

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
    is_annulled = Column(Boolean, default=False)
    
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

class SupportSettings(Base):
    __tablename__ = "support_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    notification_emails = Column(String, default="")  # Comma-separated list
    smtp_server = Column(String, default="smtp.gmail.com")
    smtp_port = Column(Integer, default=587)
    smtp_user = Column(String, default="")
    smtp_password = Column(String, default="")


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)
    recipients = Column(Text, nullable=False) # Comma-separated
    subject = Column(String, nullable=True)
    status = Column(String, default="Sent") # Sent, Failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


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
    close_comment = Column(Text, nullable=True)

class UserRole(Base):
    """Junction table for multiple role assignments per user."""
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    user = relationship("User", back_populates="extra_roles")
    role = relationship("Role")

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

# --- PROFIT AUTOMATION CONFIG ---

class ProfitAutomationConfig(Base):
    __tablename__ = "profit_automation_config"

    id = Column(Integer, primary_key=True, index=True)
    emails = Column(String, nullable=False, default="notificaciones@deliciasdebelen.com")
    cron_schedule = Column(String, default="0 8-18/1 * * 1-5") # Typical cron expression
    is_active = Column(Boolean, default=True)

class MismatchAutomationConfig(Base):
    __tablename__ = "mismatch_automation_config"

    id = Column(Integer, primary_key=True, index=True)
    emails = Column(String, nullable=False, default="notificaciones@deliciasdebelen.com")
    cron_schedule = Column(String, default="30 7,12 * * *") # 7:30 y 12:00 todos los dias
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# --- SALES FORECAST MODEL ---

class SalesForecast(Base):
    __tablename__ = "sales_forecasts"

    id = Column(Integer, primary_key=True, index=True)
    month = Column(Integer, nullable=False) # 1-12
    year = Column(Integer, nullable=False) # e.g. 2026
    co_art = Column(String, index=True, nullable=False)
    article_name = Column(String, nullable=True)
    
    # The actual algorithm suggestion (read-only history logic)
    suggested_qty = Column(Float, default=0.0) 
    
    # The final quantity approved by the manager
    estimated_qty = Column(Float, default=0.0)
    
    # To track whether the manager has overridden it
    is_adjusted = Column(Boolean, default=False)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- PROFIT PLUS REPLICAS (ETL) ---

class ProfitArticulo(Base):
    __tablename__ = "profit_articulo"

    co_art = Column(String, primary_key=True, index=True)
    art_des = Column(String, nullable=True)
    tipo = Column(String, nullable=True)
    anulado = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ProfitStockAlmacen(Base):
    __tablename__ = "profit_stock_almacen"

    id = Column(Integer, primary_key=True, autoincrement=True)
    co_art = Column(String, index=True, nullable=False)
    co_alma = Column(String, index=True, nullable=False)
    stock = Column(Float, default=0.0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ProfitFormula(Base):
    __tablename__ = "profit_formula"

    co_for = Column(String, primary_key=True, index=True)
    co_art = Column(String, index=True, nullable=False)
    fpredeterminada = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ProfitFormulaReng(Base):
    __tablename__ = "profit_formula_reng"

    id = Column(Integer, primary_key=True, autoincrement=True)
    co_for = Column(String, index=True, nullable=False)
    reng_num = Column(Integer, nullable=False)
    co_art = Column(String, index=True, nullable=False)
    cantidad = Column(Float, default=0.0)
    co_uni = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# --- PROJECTS / Trello Clone MODELS ---

class Project(Base):
    """Contenedor superior de Tableros (Fases). Un Proyecto agrupa N tableros."""
    __tablename__ = "projects"

    id          = Column(String, primary_key=True, default=generate_id)
    name        = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    background  = Column(String, default="#1e1b4b")   # Color de portada del proyecto
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    boards = relationship(
        "ProjectBoard", back_populates="project",
        cascade="all, delete-orphan", order_by="ProjectBoard.created_at"
    )
    labels = relationship(
        "ProjectLabel", back_populates="project",
        cascade="all, delete-orphan",
        primaryjoin="ProjectLabel.project_id == Project.id"
    )


class ProjectBoard(Base):
    __tablename__ = "project_boards"

    id          = Column(String, primary_key=True, default=generate_id)
    title       = Column(String, nullable=False)
    background  = Column(String, default="#714B67")
    project_id  = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="boards")
    lists   = relationship("ProjectList", back_populates="board", cascade="all, delete-orphan", order_by="ProjectList.order")

class ProjectList(Base):
    __tablename__ = "project_lists"

    id = Column(String, primary_key=True, default=generate_id)
    title = Column(String, nullable=False)
    order = Column(Float, nullable=False, default=1000.0) # Float to allow midpoint inserts (e.g., 1500)
    
    board_id = Column(String, ForeignKey("project_boards.id", ondelete="CASCADE"), index=True, nullable=False)
    board = relationship("ProjectBoard", back_populates="lists")
    
    cards = relationship("ProjectCard", back_populates="list", cascade="all, delete-orphan", order_by="ProjectCard.order")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ProjectCard(Base):
    __tablename__ = "project_cards"

    id = Column(String, primary_key=True, default=generate_id)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Float, nullable=False, default=1000.0) # Floating point sorting (1024, 2048...)
    
    list_id = Column(String, ForeignKey("project_lists.id", ondelete="CASCADE"), index=True, nullable=False)
    list = relationship("ProjectList", back_populates="cards")
    
    # Optional fields like color or label summaries
    color = Column(String, nullable=True)
    status = Column(String, nullable=False, server_default="Por Hacer")  # Por Hacer | En Proceso | Finalizado
    
    comments = relationship("ProjectComment", back_populates="card", cascade="all, delete-orphan", order_by="ProjectComment.created_at.desc()")
    
    # Relationships for Card Members (users assigned)
    members = relationship("ProjectCardMember", back_populates="card", cascade="all, delete-orphan")
    
    # Agile Card Data
    due_date = Column(DateTime(timezone=True), nullable=True)
    labels = relationship("ProjectCardLabel", back_populates="card", cascade="all, delete-orphan")
    checklists = relationship("ProjectChecklist", back_populates="card", cascade="all, delete-orphan", order_by="ProjectChecklist.created_at")
    
    # New Traza & Timeline Fields
    start_date = Column(DateTime(timezone=True), nullable=True)
    parent_id = Column(String, ForeignKey("project_cards.id", ondelete="SET NULL"), index=True, nullable=True)
    is_milestone = Column(Boolean, default=False)
    story_points = Column(Float, nullable=True, default=0.0)
    
    children = relationship("ProjectCard", backref="parent", remote_side="ProjectCard.id")
    status_history = relationship("ProjectCardStatusHistory", back_populates="card", cascade="all, delete-orphan", order_by="ProjectCardStatusHistory.timestamp")
    activity_logs = relationship("ProjectActivityLog", back_populates="card", cascade="all, delete-orphan", order_by="ProjectActivityLog.timestamp")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ProjectCardStatusHistory(Base):
    __tablename__ = "project_card_status_history"
    
    id = Column(Integer, primary_key=True, index=True)
    card_id = Column(String, ForeignKey("project_cards.id", ondelete="CASCADE"), index=True, nullable=False)
    old_list_id = Column(String, ForeignKey("project_lists.id", ondelete="SET NULL"), index=True, nullable=True)
    new_list_id = Column(String, ForeignKey("project_lists.id", ondelete="SET NULL"), index=True, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    card = relationship("ProjectCard", back_populates="status_history")
    
class ProjectActivityLog(Base):
    __tablename__ = "project_activity_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    card_id = Column(String, ForeignKey("project_cards.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action_type = Column(String, nullable=False) # e.g. "created", "updated", "moved", "commented"
    description = Column(Text, nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    card = relationship("ProjectCard", back_populates="activity_logs")
    user = relationship("User")

class ProjectComment(Base):
    __tablename__ = "project_comments"

    id = Column(String, primary_key=True, default=generate_id)
    text = Column(Text, nullable=False)
    
    card_id = Column(String, ForeignKey("project_cards.id", ondelete="CASCADE"), index=True, nullable=False)
    card = relationship("ProjectCard", back_populates="comments")
    
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    user = relationship("User")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ProjectCardMember(Base):
    __tablename__ = "project_card_members"

    id = Column(String, primary_key=True, default=generate_id)
    card_id = Column(String, ForeignKey("project_cards.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    
    card = relationship("ProjectCard", back_populates="members")
    # user relationship is unidirectional from member to User
    user = relationship("User")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- AGILE FEATURES FOR TRELLO CLONE ---

class ProjectLabel(Base):
    """Catálogo de etiquetas. Ahora pertenecen al Project (compartidas entre fases).
    board_id se mantiene como nullable para compatibilidad con registros anteriores."""
    __tablename__ = "project_labels"

    id         = Column(String, primary_key=True, default=generate_id)
    name       = Column(String, nullable=False)
    color      = Column(String, nullable=False, default="#3b82f6")

    # Relación principal: etiqueta pertenece al Proyecto
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=True)
    project    = relationship("Project", back_populates="labels", foreign_keys=[project_id])

    # Legado: se mantiene para no romper tarjetas existentes
    board_id   = Column(String, ForeignKey("project_boards.id", ondelete="SET NULL"), index=True, nullable=True)
    
class ProjectCardLabel(Base):
    """Junction between Cards and Labels"""
    __tablename__ = "project_card_labels"
    
    id = Column(String, primary_key=True, default=generate_id)
    card_id = Column(String, ForeignKey("project_cards.id", ondelete="CASCADE"), index=True, nullable=False)
    label_id = Column(String, ForeignKey("project_labels.id", ondelete="CASCADE"), index=True, nullable=False)
    
    card = relationship("ProjectCard", back_populates="labels")
    label = relationship("ProjectLabel")
    
class ProjectChecklist(Base):
    __tablename__ = "project_checklists"
    
    id = Column(String, primary_key=True, default=generate_id)
    title = Column(String, nullable=False, default="Checklist")
    
    card_id = Column(String, ForeignKey("project_cards.id", ondelete="CASCADE"), index=True, nullable=False)
    card = relationship("ProjectCard", back_populates="checklists")
    
    items = relationship("ProjectChecklistItem", back_populates="checklist", cascade="all, delete-orphan", order_by="ProjectChecklistItem.created_at")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ProjectChecklistItem(Base):
    __tablename__ = "project_checklist_items"
    
    id = Column(String, primary_key=True, default=generate_id)
    text = Column(String, nullable=False)
    is_completed = Column(Boolean, default=False)
    
    checklist_id = Column(String, ForeignKey("project_checklists.id", ondelete="CASCADE"), index=True, nullable=False)
    checklist = relationship("ProjectChecklist", back_populates="items")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
