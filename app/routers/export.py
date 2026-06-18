from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, text
from typing import Optional
from datetime import datetime

from ..database import get_db
from .. import models
from ..dependencies import get_current_active_user, check_permission
from ..services.export_engine import generate_excel

router = APIRouter(
    prefix="/reports/export",
    tags=["export"]
)

@router.get("/{report_type}")
async def export_report(
    report_type: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Security Check
    permission_map = {
        "planning": "planning",
        "production": "production",
        "logistics": "logistics", # Generic logistics permission
        "inventory": "inventory"
    }
    
    module = permission_map.get(report_type, "reports")
    if not check_permission(current_user, module, "view"):
        raise HTTPException(status_code=403, detail="Permiso Denegado")

    data = []
    columns = []
    filename = f"{report_type}_{datetime.now().strftime('%Y%m%d')}.xlsx"

    if report_type == "planning":
        query = db.query(models.ProductionPlanning)
        if start_date: query = query.filter(models.ProductionPlanning.date >= start_date)
        if end_date: query = query.filter(models.ProductionPlanning.date <= end_date)
        items = query.order_by(desc(models.ProductionPlanning.date)).all()
        
        columns = ["Fecha", "Orden", "Artículo", "Presentación", "Lotes", "Kg", "Unidades", "Cajas", "Estatus"]
        for i in items:
            data.append([
                i.date, i.order_number, i.article, i.presentation, 
                i.batches, i.kg, i.units, i.boxes, i.status
            ])

    elif report_type == "production":
        query = db.query(models.ProductionReport)
        if start_date: query = query.filter(func.date(models.ProductionReport.created_at) >= start_date)
        if end_date: query = query.filter(func.date(models.ProductionReport.created_at) <= end_date)
        items = query.order_by(desc(models.ProductionReport.created_at)).all()
        
        columns = ["Fecha", "Lote", "Producto", "Kg Prod", "Cajas", "PT Lab", "PT Quemado", "MP Desperdicio"]
        for i in items:
            data.append([
                i.created_at.strftime('%Y-%m-%d %H:%M') if i.created_at else "-",
                i.order_number, i.article_type, i.kg_produced, i.boxes,
                i.pt_lab, i.pt_burned, i.mp_waste_kg
            ])
            
    elif report_type == "logistics_reception":
        # Combines MP and PT? Or split? User usually sees tabs. Let's export "Merchandise" (MP) as default or handle sub-types
        # Let's support specific keys
        pass

    elif report_type == "reception_merchandise":
        query = db.query(models.LogisticsReceptionMerchandise)
        if start_date: query = query.filter(func.date(models.LogisticsReceptionMerchandise.date) >= start_date)
        if end_date: query = query.filter(func.date(models.LogisticsReceptionMerchandise.date) <= end_date)
        items = query.order_by(desc(models.LogisticsReceptionMerchandise.date)).all()
        
        columns = ["Fecha", "Proveedor", "Documento", "Items (JSON)"]
        for i in items:
            data.append([
                i.date.strftime('%Y-%m-%d %H:%M'), i.supplier, i.document_ref, i.items_json
            ])
            
    elif report_type == "reception_production":
        query = db.query(models.LogisticsReceptionProduction)
        if start_date: query = query.filter(func.date(models.LogisticsReceptionProduction.date) >= start_date)
        if end_date: query = query.filter(func.date(models.LogisticsReceptionProduction.date) <= end_date)
        items = query.order_by(desc(models.LogisticsReceptionProduction.date)).all()
        
        columns = ["Fecha", "Producto", "Cantidad", "Reporte ID", "Notas"]
        for i in items:
            data.append([
                i.date.strftime('%Y-%m-%d %H:%M'), i.product_name, i.quantity, i.production_report_id, i.notes
            ])

    elif report_type == "dispatch":
        query = db.query(models.LogisticsDispatch)
        if start_date: query = query.filter(func.date(models.LogisticsDispatch.date) >= start_date)
        if end_date: query = query.filter(func.date(models.LogisticsDispatch.date) <= end_date)
        items = query.order_by(desc(models.LogisticsDispatch.date)).all()
        
        columns = ["Fecha", "Cliente", "Documento", "Ruta", "Items (Raw)"]
        for i in items:
            route_name = i.route.name if i.route else "-"
            data.append([
                i.date.strftime('%Y-%m-%d %H:%M'), i.client_destination, i.document_ref, route_name, i.items_json
            ])
            
    elif report_type == "inventory":
        query = db.query(models.InventoryCaptureHeader)
        if start_date: query = query.filter(models.InventoryCaptureHeader.date >= start_date)
        if end_date: query = query.filter(models.InventoryCaptureHeader.date <= end_date)
        items = query.order_by(desc(models.InventoryCaptureHeader.date)).all()
        
        columns = ["Fecha", "Correlativo", "Usuario", "Estatus", "Notas"]
        for i in items:
            uname = i.user.username if i.user else "Unknown"
            data.append([
                i.date.strftime('%Y-%m-%d %H:%M') if i.date else "-", 
                i.correlative, uname, i.status, i.notes
            ])

    else:
        raise HTTPException(status_code=404, detail="Tipo de reporte no soportado")

    excel_file = generate_excel(data, columns, title=report_type.upper())
    
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"'
    }
    
    return StreamingResponse(
        excel_file, 
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
        headers=headers
    )
