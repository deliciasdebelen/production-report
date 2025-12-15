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
    total_planned_batches: int
    total_planned_kg: float
    total_planned_units: int
    yield_percentage: float
    compliance_percentage: float
    waste_percentage: float = 0.0
    avg_kg_per_batch: float = 0.0
    
    # Chart Data
    pie_data: list[dict] = [] # [{'label': 'Mayonesa', 'value': 1500.00}]
    history_data: list[dict] = [] # [{'date': '2025-12-01', 'produced': 100, 'planned': 120}]

