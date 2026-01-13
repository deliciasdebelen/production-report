from fastapi import APIRouter, Depends, HTTPException, Request, Form
from sqlalchemy.orm import Session
from sqlalchemy import desc, text
from typing import Optional, List
from ..external_db import get_external_db
import json
from datetime import datetime

from ..dependencies import get_db, templates, get_current_user
from ..models import LogisticsReceptionProduction, LogisticsReceptionMerchandise, LogisticsDispatch, User, ProductionReport

router = APIRouter(
    prefix="/logistics",
    tags=["logistics"],
    responses={404: {"description": "Not found"}},
)

# --- Views ---

@router.get("/")
async def logistics_dashboard(request: Request, user: User = Depends(get_current_user)):
    if user.role not in [1, 3, 4, 5]: # Logic/Admin/Planner/Almacen
        raise HTTPException(status_code=403, detail="Not authorized")
    return templates.TemplateResponse("logistics/dashboard.html", {
        "request": request,
        "user": user,
        "title": "Logística"
    })

@router.get("/inventory")
async def view_logistics_inventory(request: Request, user: User = Depends(get_current_user)):
    if user.role not in [1, 3, 4, 5, 6]: # All logistics roles inc Inventory
        raise HTTPException(status_code=403, detail="Not authorized")
    return templates.TemplateResponse("logistics/inventory.html", {
        "request": request,
        "user": user,
        "title": "Control de Inventario"
    })

@router.get("/reception/production")
async def view_reception_production(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in [1, 3, 4, 5]:
        raise HTTPException(status_code=403, detail="Not authorized")
    logs = db.query(LogisticsReceptionProduction).order_by(desc(LogisticsReceptionProduction.date)).limit(50).all()
    return templates.TemplateResponse("logistics/reception_production.html", {
        "request": request, 
        "user": user, 
        "logs": logs,
        "title": "Recepción de Producción"
    })

@router.get("/reception/merchandise")
async def view_reception_merchandise(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in [1, 3, 4, 5]:
        raise HTTPException(status_code=403, detail="Not authorized")
    logs = db.query(LogisticsReceptionMerchandise).order_by(desc(LogisticsReceptionMerchandise.date)).limit(50).all()
    # Parse JSON items for display
    for log in logs:
        try:
            log.items = json.loads(log.items_json)
        except:
            log.items = []
            
    return templates.TemplateResponse("logistics/reception_merchandise.html", {
        "request": request, 
        "user": user, 
        "logs": logs,
        "title": "Recepción de Mercancía"
    })

@router.get("/dispatch")
async def view_dispatch(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in [1, 3, 4, 5]:
        raise HTTPException(status_code=403, detail="Not authorized")
    logs = db.query(LogisticsDispatch).order_by(desc(LogisticsDispatch.date)).limit(50).all()
    for log in logs:
        try:
            log.items = json.loads(log.items_json)
        except:
            log.items = []

    return templates.TemplateResponse("logistics/dispatch.html", {
        "request": request, 
        "user": user, 
        "logs": logs,
        "title": "Despacho de Mercancía"
    })

# --- API Actions ---

@router.get("/api/clients/search")
async def search_clients(
    q: str, 
    user: User = Depends(get_current_user),
    db: Session = Depends(get_external_db)
):
    if not q or len(q) < 2:
        return []
    
    try:
        # Search by code or description, top 10 results
        sql = text("""
            SELECT TOP 10 co_cli, cli_des 
            FROM sacliente 
            WHERE (co_cli LIKE :search OR cli_des LIKE :search)
            AND inactivo = 0
            ORDER BY cli_des
        """)
        
        # Use simple wildcard search
        search_pattern = f"%{q}%"
        result = db.execute(sql, {"search": search_pattern}).fetchall()
        
        return [{"co_cli": row.co_cli.strip(), "cli_des": row.cli_des.strip()} for row in result]
        
    except Exception as e:
        print(f"Error searching clients: {e}")
        # Return empty list or mock if connection fails (graceful degradation)
        return []

@router.get("/api/external/client/{co_cli}/pending-invoices")
async def get_pending_invoices(
    co_cli: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_external_db),
    local_db: Session = Depends(get_db)
):
    """
    Executes SP_CRM_FacturasPendientesPorCliente @co_cli
    Returns list of items pending to be dispatched.
    """
    try:
        # Check Local History for Duplicate Invoices
        # Search last 200 dispatches for this client to find used invoice numbers
        dispatches = local_db.query(LogisticsDispatch.document_ref)\
            .filter(LogisticsDispatch.document_ref.isnot(None))\
            .filter(LogisticsDispatch.client_destination.contains(co_cli))\
            .order_by(desc(LogisticsDispatch.date)).limit(200).all()
            
        used_invoices = set()
        import re
        for d in dispatches:
            if d.document_ref:
                # Extract all number sequences that look like our invoices (usually > 1 digit)
                nums = re.findall(r'\b\d+\b', d.document_ref)
                used_invoices.update(nums)

        # Execute SP
        sql = text("EXEC SP_CRM_FacturasPendientesPorCliente @co_cli = :cli")
        result_proxy = db.execute(sql, {"cli": co_cli})
        keys = result_proxy.keys()
        # print(f"--- DEBUG COLS: {keys} ---") # Keep this useful for now if needed, or rely on logic below
        
        result = result_proxy.fetchall()

        def get_col(row_map, candidates):
            # Try exact match first
            for c in candidates:
                if c in row_map: return row_map[c]
            # Try case-insensitive strip match
            keys = list(row_map.keys())
            for c in candidates:
                for k in keys:
                    if c.lower() in k.lower(): return row_map[k]
            return None

        items = []
        for row in result:
             row_map = row._mapping
             
             # Robust Mapping
             fact_num = str(get_col(row_map, ['Número Factura', 'fact_num', 'Numero Factura']) or "UNKNOWN").strip()
             
             # FILTER: If invoice is already in history, skip
             if fact_num in used_invoices:
                 continue

             co_art = get_col(row_map, ['Código Artículo', 'co_art', 'Codigo Articulo']) or ""
             art_des = get_col(row_map, ['Descripción Artículo', 'art_des', 'Descripcion Articulo']) or ""
             co_uni = get_col(row_map, ['Unidad', 'co_uni', 'Unid', 'UND']) or "UNI"
             
             items.append({
                "fact_num": str(fact_num).strip(), 
                "co_art": str(co_art).strip(),
                "art_des": str(art_des).strip(),
                "co_uni": str(co_uni).strip(),
                "total_art": 1.0 
             })
            
        return items
        
    except Exception as e:
        print(f"Error executing SP_CRM_FacturasPendientesPorCliente: {e}")
        return []




# ... existing code ...

@router.get("/api/production/pending")
async def get_pending_production(
    order_id: Optional[str] = None,
    date_start: Optional[str] = None,
    date_end: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    query = db.query(ProductionReport).filter(ProductionReport.status == "Pending")
    
    if order_id:
        query = query.filter(ProductionReport.order_number.contains(order_id))
    
    if date_start:
        try:
            # Assume YYYY-MM-DD coming from frontend date input
            d_start = datetime.strptime(date_start, "%Y-%m-%d")
            query = query.filter(ProductionReport.created_at >= d_start)
        except ValueError:
            pass # Ignore invalid dates
            
    if date_end:
        try:
            d_end = datetime.strptime(date_end, "%Y-%m-%d")
            # Set to end of day
            d_end = d_end.replace(hour=23, minute=59, second=59)
            query = query.filter(ProductionReport.created_at <= d_end)
        except ValueError:
            pass

    reports = query.order_by(ProductionReport.created_at.desc()).all()
    
    return [{
        "id": r.id,
        "order_number": r.order_number,
        "article_type": r.article_type,
        "pt_units": r.pt_units,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "status": r.status
    } for r in reports]

@router.post("/reception/confirm")
async def confirm_reception(
    production_id: str = Form(...),
    received_qty: int = Form(...), # Received Units
    alert_email: Optional[str] = Form(None), # If discrepancy, send here
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    report = db.query(ProductionReport).filter(ProductionReport.id == production_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    # 1. Validation
    # logic: compare report.pt_units with received_qty
    discrepancy = report.pt_units - received_qty
    
    if discrepancy != 0:
        # 2. Email Alert Logic (Mock)
        if alert_email:
            print(f"--- [MOCK EMAIL] ---")
            print(f"To: {alert_email}")
            print(f"Subject: Alerta de Merma - Orden {report.order_number}")
            print(f"Body: Se detectó una diferencia de {discrepancy} unidades en la recepción de la orden {report.order_number}.")
            print(f"--------------------")
    
    # 3. Update Status
    report.status = "Confirmed"
    
    # 4. Log the Reception event
    # Calculate boxes/kg for the log based on received_qty
    # We need to reuse the presentation logic or just store raw units for now. 
    # Let's simple-store raw units.
    
    new_log = LogisticsReceptionProduction(
        production_report_id=report.id,
        product_name=report.article_type, # Using article name
        quantity=received_qty,
        notes=f"Recibido por {user.username}. Diferencia: {discrepancy}"
    )
    db.add(new_log)
    db.commit()
    
    return {"status": "success", "discrepancy": discrepancy}

# ... existing dispatch ...

@router.post("/reception/merchandise")
async def create_reception_merchandise(
    supplier: str = Form(...),
    document_ref: str = Form(...),
    items: str = Form(...), # JSON string
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_log = LogisticsReceptionMerchandise(
        supplier=supplier,
        document_ref=document_ref,
        items_json=items
    )
    db.add(new_log)
    db.commit()
    return {"status": "success"}

@router.post("/dispatch")
async def create_dispatch(
    client_destination: str = Form(...), # Fallback/Search Input
    document_ref: str = Form(...), # Mandatory now
    imported_invoices: str = Form(None), 
    items: str = Form(...), # JSON string
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Mandatory Guide Validation
    if not document_ref or not document_ref.strip():
        raise HTTPException(status_code=400, detail="El Número de Guía es obligatorio.")
    
    # 2. Unique Guide Validation (Global)
    exists = db.query(LogisticsDispatch).filter(LogisticsDispatch.document_ref.like(f"{document_ref.strip()}%")).first()
    # Note: Using LIKE because we append "| Fact: ..." to the ref. 
    # Or strict check? User said "Guide number cannot repeat".
    # If we store "1234 | Fact: ...", checking "1234" might fail exact match.
    # Better: Check startswith or exact. 
    # Let's assume the user enters "1234" and we store "1234 | Fact: X".
    # Checking "1234" against "1234 | Fact: X" requires LIKE '1234%'.
    
    existing_guide = db.query(LogisticsDispatch).filter(
        LogisticsDispatch.document_ref.like(f"{document_ref.strip()} | %") 
        | (LogisticsDispatch.document_ref == document_ref.strip())
    ).first()
    
    if existing_guide:
        raise HTTPException(status_code=400, detail=f"El Número de Guía {document_ref} ya existe en el sistema.")

    # 3. Determine Final Client (Multi-Client Support)
    try:
        items_list = json.loads(items)
        distinct_clients = set()
        for i in items_list:
            if 'client' in i and i['client']:
                distinct_clients.add(i['client'])
        
        final_client = client_destination # Default to form input
        if len(distinct_clients) > 1:
            final_client = "Multi-Destino" # Or " / ".join(distinct_clients)
        elif len(distinct_clients) == 1:
            final_client = list(distinct_clients)[0]
            
    except:
        final_client = client_destination # Fallback

    # 4. Concatenate Invoices to Reference
    final_ref = document_ref.strip()
    if imported_invoices:
        # Check for Duplicate Invoices (Previous Logic - Global Check?)
        # Let's keep it safe: Check provided invoices against history?
        # User emphasized Guide Number uniqueness heavily this time.
        # But let's keep the invoice check if possible, though maybe less strict if guide is unique?
        # Proceeding with strict Guide Check as primary request.
        
        final_ref += f" | Fact: {imported_invoices}"
            
    new_log = LogisticsDispatch(
        client_destination=final_client,
        document_ref=final_ref,
        items_json=items
    )
    db.add(new_log)
    db.commit()
    return {"status": "success"}
