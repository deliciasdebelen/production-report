from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date

class ProductionReportBase(BaseModel):
    batch_qty: int
    article_type: str
    kg_produced: float
    presentation: str
    boxes: float = 0.0
    pt_units: int = 0
    pt_lab: int = 0
    pt_burned: int = 0
    mp_containers: int = 0
    mp_caps_clean: int = 0
    mp_caps_dirty: int = 0
    mp_waste_kg: float = 0.0
    mp_waste_image: Optional[str] = None
    cons_type: Optional[str] = None
    cons_count: float = 0.0
    cons_unit_weight: float = 0.0
    cons_qty: float = 0.0
    notes: Optional[str] = None

class ProductionReportCreate(ProductionReportBase):
    custom_created_at: Optional[date] = None # For admin overrides

class ProductionReport(ProductionReportBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True

class ProductionPlanningBase(BaseModel):
    date: str
    article: str
    presentation: str
    batches: int = 0
    kg: float = 0.0
    units: int = 0
    boxes: float = 0.0
    units: int = 0
    boxes: float = 0.0
    waste_percentage: float = 0.0
    waste_kg: float = 0.0
    status: Optional[str] = "Pending"
    notes: Optional[str] = None

class ProductionPlanningCreate(ProductionPlanningBase):
    pass

class ProductionPlanning(ProductionPlanningBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_production_batches: int
    total_production_kg: float
    total_production_units: int
    total_production_boxes: float = 0.0
    total_waste_kg: float = 0.0
    total_planned_batches: int
    total_planned_kg: float
    total_planned_units: int
    yield_percentage: float
    compliance_percentage: float
    waste_percentage: float = 0.0
    avg_kg_per_batch: float = 0.0
    quick_consumption_percentage: float = 0.0
    
    # Chart Data
    pie_data: list[dict] = [] # [{'label': 'Mayonesa', 'value': 1500.00}]
    history_data: list[dict] = [] # [{'date': '2025-12-01', 'produced': 100, 'planned': 120}]

# Inventory Schemas
class InventoryCaptureBase(BaseModel):
    capture_type: str
    article_code: str
    article_description: str
    batch: str
    quantity: float
    capture_date: str
    capture_time: str
    department: Optional[str] = None
    out_of_range: bool = False

class InventoryCaptureCreate(InventoryCaptureBase):
    pass

class InventoryCapture(InventoryCaptureBase):
    id: int
    user_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True


# Inventory Schemas (Master-Detail)

class InventoryLineBase(BaseModel):
    article_code: str
    article_description: str
    batch: str
    quantity: float

class InventoryLineCreate(InventoryLineBase):
    pass

class InventoryLine(InventoryLineBase):
    id: int
    header_id: int
    
    class Config:
        from_attributes = True

class InventoryHeaderBase(BaseModel):
    date: datetime
    notes: Optional[str] = None

class InventoryHeaderCreate(InventoryHeaderBase):
    lines: list[InventoryLineCreate]

class InventoryHeader(InventoryHeaderBase):
    id: int
    correlative: str
    status: str
    user_id: int
    # created_at removed to match model 'date'
    lines: list[InventoryLine] = []
    
    
    class Config:
        from_attributes = True

class LogisticsRouteBase(BaseModel):
    name: str
    active: bool = True

class LogisticsRouteCreate(LogisticsRouteBase):
    pass

class LogisticsRoute(LogisticsRouteBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- SUPPORT MODULE SCHEMAS ---

class SupportBase(BaseModel):
    name: str

class SupportDepartment(SupportBase):
    id: int
    class Config:
        from_attributes = True

class SupportStatus(SupportBase):
    id: int
    color_hex: str
    class Config:
        from_attributes = True

class SupportPriority(SupportBase):
    id: int
    level: int
    class Config:
        from_attributes = True

class SupportType(SupportBase):
    id: int
    class Config:
        from_attributes = True

class SupportTicketBase(BaseModel):
    description: str
    attachment_url: Optional[str] = None
    contact_email: Optional[str] = None
    department_id: int
    type_id: int
    priority_id: int

class SupportTicketCreate(SupportTicketBase):
    pass

class SupportTicketUpdate(BaseModel):
    status_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    priority_id: Optional[int] = None

class SupportTicket(SupportTicketBase):
    id: int
    code: str
    created_by_id: int
    status_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    created_at: datetime
    closed_at: Optional[datetime] = None
    
    # Relationships (Simplified for listing)
    department: Optional[SupportDepartment] = None
    status: Optional[SupportStatus] = None
    priority: Optional[SupportPriority] = None
    support_type: Optional[SupportType] = None
    created_by_username: Optional[str] = None # Calculated field

    class Config:
        from_attributes = True
