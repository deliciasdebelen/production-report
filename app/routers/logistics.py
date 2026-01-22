from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, text
from typing import Optional, List
from ..external_db import get_external_db
import json
from datetime import datetime
import re

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
    if not user:
        return RedirectResponse(url="/login")
    if user.role not in [1, 3, 4, 5]: # Logic/Admin/Planner/Almacen
        raise HTTPException(status_code=403, detail="Not authorized")
    return templates.TemplateResponse("logistics/dashboard.html", {
        "request": request,
        "user": user,
        "title": "Logística"
    })

@router.get("/inventory")
async def view_logistics_inventory(request: Request, user: User = Depends(get_current_user)):
    if not user: return RedirectResponse("/login")
    if user.role not in [1, 3, 4, 5, 6]: # All logistics roles inc Inventory
        raise HTTPException(status_code=403, detail="Not authorized")
    return templates.TemplateResponse("inventory.html", {
        "request": request,
        "user": user,
        "title": "Control de Inventario"
    })

@router.get("/reception/production")
async def view_reception_production(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user: return RedirectResponse("/login")
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
    if not user: return RedirectResponse("/login")
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
    if not user: return RedirectResponse("/login")
    if user.role not in [1, 3, 4, 5]:
        raise HTTPException(status_code=403, detail="Not authorized")
    logs = db.query(LogisticsDispatch).order_by(desc(LogisticsDispatch.date)).limit(50).all()
    for log in logs:
        try:
            log.items = json.loads(log.items_json)
        except:
            log.items = []

    next_ref = generate_next_guide_number(db)
    return templates.TemplateResponse("logistics/dispatch.html", {
        "request": request, 
        "user": user, 
        "logs": logs,
        "title": "Despacho de Mercancía",
        "next_guide_number": next_ref
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


@router.get("/api/external/invoice/{doc_num}/items")
async def get_invoice_items(
    doc_num: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_external_db),
    local_db: Session = Depends(get_db)
):
    """
    Get items for a SPECIFIC invoice.
    Can reuse the logic of 'pending invoices by client' but filtered for this invoice.
    Or maybe there is a direct query/SP?
    User said 'follow the process as defined', implies reusing the SP logic but for a known invoice.
    Strategy:
    1. Find the Client of this Invoice.
    2. Call the SAME 'facturas pendientes' logic (SP) for that client.
    3. Filter the result to return ONLY this invoice's items.
    """
    try:
        # 1. Get Client Code
        invoice_row = db.execute(text("SELECT co_cli, cli_des FROM safactura WHERE doc_num = :d"), {"d": doc_num}).fetchone()
        if not invoice_row:
            return {"error": "Factura no encontrada"}
        
        co_cli = invoice_row.co_cli.strip()
        cli_des = invoice_row.cli_des.strip()
        
        # 2. Re-use existing logic (copy-paste or call? copy-paste safer for quick edit)
        # Execute SP for Client
        sql = text("EXEC SP_CRM_FacturasPendientesPorCliente @co_cli = :cli")
        result_proxy = db.execute(sql, {"cli": co_cli})
        result = result_proxy.fetchall()

        def get_col(row_map, candidates):
            for c in candidates:
                if c in row_map: return row_map[c]
            keys = list(row_map.keys())
            for c in candidates:
                for k in keys:
                    if c.lower() in k.lower(): return row_map[k]
            return None

        final_items = []
        
        for row in result:
             row_map = row._mapping
             
             fact_num_row = str(get_col(row_map, ['Número Factura', 'fact_num', 'Numero Factura']) or "").strip()
             
             # FILTER: Only this invoice
             # Note: SP might return formatted number? doc_num usually matches.
             # Let's match loosely or exact.
             if fact_num_row != doc_num:
                 continue
                 
             co_art = str(get_col(row_map, ['Código Artículo', 'co_art', 'Codigo Articulo']) or "").strip()
             art_des = str(get_col(row_map, ['Descripción Artículo', 'art_des', 'Descripcion Articulo']) or "").strip()
             co_uni = str(get_col(row_map, ['Unidad', 'co_uni', 'Unid', 'UND']) or "UNI").strip()
             
             raw_units = get_col(row_map, ['Total Articulo', 'total_articulo', 'total_art', 'unidades'])
             raw_boxes = get_col(row_map, ['Cantidad Cajas', 'cantidad_cajas', 'cajas'])
             raw_box_unit = get_col(row_map, ['Unidad Cajas', 'unidad_cajas']) or "CAJ"

             try: units = float(raw_units) if raw_units is not None else 1.0
             except: units = 1.0
             try: boxes = float(raw_boxes) if raw_boxes is not None else 0.0
             except: boxes = 0.0

             if not co_art: continue

             final_items.append({
                 "fact_num": fact_num_row, 
                 "co_art": co_art,
                 "art_des": art_des,
                 "co_uni": co_uni, 
                 "total_articulo": units,
                 "total_cajas": round(boxes, 2),
                 "unidad_cajas": raw_box_unit,
                 "client_name": cli_des # Include client name for frontend display
             })
             
        # Aggregate same SKU in same invoice? 
        # Reuse logic? Yes, simpler to just return list and let frontend or helper aggregate.
        # But wait, frontend expects aggregated?
        # Let's aggregate here to avoid duplicates in display.
        aggregated = {}
        for i in final_items:
            key = i['co_art']
            if key not in aggregated:
                aggregated[key] = i
            else:
                aggregated[key]['total_articulo'] += i['total_articulo']
                aggregated[key]['total_cajas'] += i['total_cajas']
                
        return list(aggregated.values())
        
    except Exception as e:
        print(f"Error fetching invoice items: {e}")
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
    Returns list of items pending to be dispatched, grouped by Article.
    """
    try:
        # Check Local History for Duplicate Invoices
        dispatches = local_db.query(LogisticsDispatch.document_ref)\
            .filter(LogisticsDispatch.document_ref.isnot(None))\
            .filter(LogisticsDispatch.client_destination.contains(co_cli))\
            .order_by(desc(LogisticsDispatch.date)).limit(200).all()
            
        used_invoices = set()
        import re
        for d in dispatches:
            if d.document_ref:
                nums = re.findall(r'\b\d+\b', d.document_ref)
                used_invoices.update(nums)

        # Execute SP
        sql = text("EXEC SP_CRM_FacturasPendientesPorCliente @co_cli = :cli")
        result_proxy = db.execute(sql, {"cli": co_cli})
        result = result_proxy.fetchall()

        def get_col(row_map, candidates):
            for c in candidates:
                if c in row_map: return row_map[c]
            keys = list(row_map.keys())
            for c in candidates:
                for k in keys:
                    if c.lower() in k.lower(): return row_map[k]
            return None

        # Grouping Dictionary: (fact_num, co_art) -> Data
        grouped_items = {}

        for row in result:
             row_map = row._mapping
             
             fact_num = str(get_col(row_map, ['Número Factura', 'fact_num', 'Numero Factura']) or "UNKNOWN").strip()
             
             if fact_num in used_invoices:
                 continue

             co_art = str(get_col(row_map, ['Código Artículo', 'co_art', 'Codigo Articulo']) or "").strip()
             art_des = str(get_col(row_map, ['Descripción Artículo', 'art_des', 'Descripcion Articulo']) or "").strip()
             co_uni = str(get_col(row_map, ['Unidad', 'co_uni', 'Unid', 'UND']) or "UNI").strip()
             
             # Extract Quantity & Boxes directly from SP
             # User confirmed columns: "Total Articulo", "Cantidad Cajas", "Unidad Cajas"
             
             raw_units = get_col(row_map, ['Total Articulo', 'total_articulo', 'total_art', 'unidades'])
             raw_boxes = get_col(row_map, ['Cantidad Cajas', 'cantidad_cajas', 'cajas'])
             raw_box_unit = get_col(row_map, ['Unidad Cajas', 'unidad_cajas']) or "CAJ"

             try:
                 units = float(raw_units) if raw_units is not None else 1.0
             except:
                 units = 1.0
                 
             try:
                 boxes = float(raw_boxes) if raw_boxes is not None else 0.0
             except:
                 boxes = 0.0

             if not co_art:
                 continue

             key = (fact_num, co_art)

             if key not in grouped_items:
                 grouped_items[key] = {
                     "fact_num": fact_num,
                     "co_art": co_art,
                     "art_des": art_des,
                     "co_uni": co_uni,
                     "total_articulo": 0.0,
                     "total_cajas": 0.0,
                     "unidad_cajas": raw_box_unit
                 }
             
             grouped_items[key]["total_articulo"] += units
             grouped_items[key]["total_cajas"] += boxes

        # Flatten (No extra queries needed)
        final_items = []
        
        for key, data in grouped_items.items():
            final_items.append({
                "fact_num": data["fact_num"], 
                "co_art": data["co_art"],
                "art_des": data["art_des"],
                "co_uni": data["co_uni"], 
                "total_articulo": data["total_articulo"],
                "total_cajas": round(data["total_cajas"], 2),
                "unidad_cajas": data["unidad_cajas"]
             })
            
        return final_items
        
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
    request: Request,
    document_ref: str = Form(...), # Mandatory now
    imported_invoices: str = Form(None), 
    items: str = Form(...), # JSON string
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    external_db: Session = Depends(get_external_db)
):
    # Manual Form Parsing to Bypass "Field required" persistence
    # Pydantic/FastAPI was refusing to accept the missing/empty field despite Optional[str]
    form_data = await request.form()
    client_destination = form_data.get("client_destination", "")
    # 1. Mandatory Guide Validation
    # Allow "(Generado Automáticamente)" or empty to trigger auto-gen
    if not document_ref or not document_ref.strip() or document_ref == '(Generado Automáticamente)':
         document_ref = generate_next_guide_number(db)
    
    # Re-validate just in case
    if not document_ref:
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
    # 4. Concatenate Invoices to Reference
    final_ref = document_ref.strip()
    if imported_invoices:
        final_ref += f" | Fact: {imported_invoices}"

    # 5. Calculate Dispatch Summary & Enrich Items (BEFORE SAVING)
    summary_data = [] # For Response
    enriched_items = [] # For DB Storage
    
    try:
        # Group by SKU for Summary Response
        sku_totals = {}
        
        # Parse Input Items
        input_items_list = json.loads(items) 
        
        # Determine Equivalencies for EACH item and enrich it
        # Note: We also calculate the global summary
        
        for item in input_items_list:
            raw_item = item.get('item', '')
            qty = float(item.get('qty', 0))
            unit = item.get('unit', 'Unid')
            
            # Extract SKU
            sku_match = re.search(r'\((.*?)\)$', raw_item)
            sku = sku_match.group(1).strip() if sku_match else raw_item.strip()
            
            # --- Per-Item Breakdown Calculation (Best Effort) ---
            item_breakdown = f"{qty} {unit}" # Default
            try:
                 # Fetch units from external DB for this SKU
                rows = external_db.execute(
                    text("SELECT co_uni, equivalencia FROM saArtUnidad WHERE co_art = :sku"), 
                    {"sku": sku}
                ).fetchall()
                
                if rows:
                    base_unit = "UNI"
                    pack_unit = "UNI"
                    pack_factor = 1.0
                    
                    # 1. Find Base (Equiv = 1)
                    for r in rows:
                        if r.equivalencia == 1:
                            base_unit = r.co_uni.strip()
                            
                    # 2. Find Max Pack (Equiv > 1)
                    max_equiv = 1.0
                    for r in rows:
                        if r.equivalencia > 1 and r.equivalencia > max_equiv:
                            max_equiv = float(r.equivalencia)
                            pack_unit = r.co_uni.strip()
                            pack_factor = max_equiv
                    
                    # 3. Calculate breakdown if unit is "Unid" or similar
                    # If user engaged "Unid", we break it down. 
                    # If user engaged "Cjas", we might want to show total units? 
                    # Let's stick to the "Boxes + Units" logic found previously.
                    
                    if pack_factor > 1:
                        # Normalize to base units first? 
                        # Assuming input qty is in base units if unit == base_unit.
                        # What if unit is 'Cjas'? 
                        # Let's assume input 'qty' is always treated as base units for now OR strictly follow what user inputs.
                        # The previous logic treated 'qty' as raw.
                        
                        # Calculation Logic
                        boxes = int(qty // pack_factor)
                        loose = qty % pack_factor
                        
                        parts = []
                        if boxes > 0:
                            parts.append(f"{boxes} {pack_unit}")
                        if loose > 0 or boxes == 0:
                            loose_fmt = f"{int(loose)}" if loose.is_integer() else f"{loose:.2f}"
                            parts.append(f"{loose_fmt} {base_unit}")
                        
                        item_breakdown = " + ".join(parts)
            except Exception as e:
                print(f"Error calculating per-item breakdown: {e}")
            
            # Add to Enriched Item
            item['breakdown'] = item_breakdown
            enriched_items.append(item)

            # --- Add to Global Summary ---
            if sku not in sku_totals:
                sku_totals[sku] = {'qty': 0.0, 'name': raw_item, 'breakdown': ''}
            sku_totals[sku]['qty'] += qty

        # Finalize Global Summary (Re-calculate breakdown on total qty)
        for sku, data in sku_totals.items():
            total_qty = data['qty']
            total_breakdown = f"{total_qty}"
            
            # Re-run calc for total (Optimization: could functionize this)
            try:
                rows = external_db.execute(text("SELECT co_uni, equivalencia FROM saArtUnidad WHERE co_art = :sku"), {"sku": sku}).fetchall()
                if rows:
                    base_unit = "UNI"; pack_unit = "UNI"; pack_factor = 1.0; 
                    for r in rows: 
                        if r.equivalencia == 1: base_unit = r.co_uni.strip()
                    for r in rows: 
                        if r.equivalencia > 1 and r.equivalencia > max_equiv: max_equiv = float(r.equivalencia); pack_unit = r.co_uni.strip(); pack_factor = max_equiv
                    
                    if pack_factor > 1:
                        boxes = int(total_qty // pack_factor)
                        loose = total_qty % pack_factor
                        parts = []
                        if boxes > 0: parts.append(f"{boxes} {pack_unit}")
                        if loose > 0 or boxes == 0: loose_fmt = f"{int(loose)}" if loose.is_integer() else f"{loose:.2f}"; parts.append(f"{loose_fmt} {base_unit}")
                        total_breakdown = " + ".join(parts)
                    else:
                        total_breakdown = f"{total_qty} {base_unit}"
            except: pass

            summary_data.append({
                "sku": sku,
                "name": data['name'],
                "total": total_qty,
                "breakdown": total_breakdown
            })

    except Exception as e:
        print(f"Error in dispatch calculation: {e}")
        # Fallback: Just save raw items if calc fails
        enriched_items = json.loads(items)

    # 6. Save to DB
    new_log = LogisticsDispatch(
        client_destination=final_client,
        document_ref=final_ref,
        items_json=json.dumps(enriched_items) # Save Enriched JSON
    )
    db.add(new_log)
    db.commit()

    return {
        "status": "success", 
        "summary": summary_data, 
        "document_ref": final_ref,
        "id": new_log.id
    }

@router.get("/dispatch/{dispatch_id}/print", response_class=HTMLResponse)
async def print_dispatch(
    dispatch_id: int,
    request: Request,
    db: Session = Depends(get_db),
    external_db: Session = Depends(get_external_db)
):
    log = db.query(LogisticsDispatch).filter(LogisticsDispatch.id == dispatch_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Despacho no encontrado")
        
    # Parse items
    try:
        raw_items = json.loads(log.items_json)
    except:
        raw_items = []

    # --- Aggregation Logic ---
    # --- Aggregation Logic (Group by Invoice + SKU) ---
    # We want to group everything under Invoices.
    # Structure:
    # aggregated_data = {
    #    "000123": { "SKU1": { ...data... } }
    # }
    
    aggregated_data = {}
    invoice_clients = {} # Map invoice -> client name
    
    # 1. Collect unique invoices to query DB
    unique_invoices = set()
    for item in raw_items:
        inv = item.get('fact')
        if inv and inv.strip():
            unique_invoices.add(inv.strip())
            
    # 2. Query Client Names
    try:
        data_invs = list(unique_invoices)
        if data_invs:
            # Safe parameterized IN clause is tricky in raw SQL, loop is safer for small sets
            for inv_num in data_invs:
                # Assuming saFacturaVenta links to saCliente via co_cli
                # We need the client NAME (des_cli from saCliente, or potentially stored in header)
                # saFacturaVenta usually has 'co_cli'. We join saCliente.
                query = text("""
                    SELECT c.descrip 
                    FROM saFacturaVenta f
                    JOIN saCliente c ON f.co_cli = c.co_cli
                    WHERE f.doc_num = :doc_num
                """)
                row = external_db.execute(query, {"doc_num": inv_num}).first()
                if row:
                    invoice_clients[inv_num] = row[0].strip()
                else:
                    invoice_clients[inv_num] = "Cliente Desconocido"
    except Exception as e:
        print(f"Error fetching invoice clients: {e}")

    for item in raw_items:
        # 1. Identify Invoice
        invoice = item.get('fact')
        if not invoice or invoice.strip() == '':
            invoice = "Otros / Manual"
        else:
            invoice = invoice.strip()
            
        # 2. Identify SKU/Target
        raw_name = item.get('name', item.get('item', 'Unknown'))
        sku = item.get('sku')
        if not sku:
             sku_match = re.search(r'\((.*?)\)$', raw_name)
             sku = sku_match.group(1).strip() if sku_match else raw_name.strip()
             
        # 3. Values
        try:
            qty = float(item.get('qty', 0))
        except: qty = 0.0
        
        unit = item.get('unit', 'UNID')
        
        # New Fields (Imported)
        try:
            imported_boxes = float(item.get('total_cajas', 0))
        except: imported_boxes = 0.0
        imported_box_unit = item.get('unidad_cajas', 'CAJ')

        # 4. Aggregate
        if invoice not in aggregated_data:
            aggregated_data[invoice] = {}
        
        if sku not in aggregated_data[invoice]:
            aggregated_data[invoice][sku] = {
                'sku': sku,
                'name': raw_name,
                'qty': 0.0,
                'unit': unit,
                'total_cajas': 0.0,
                'unidad_cajas': imported_box_unit 
            }
        
        aggregated_data[invoice][sku]['qty'] += qty
        aggregated_data[invoice][sku]['total_cajas'] += imported_boxes
        # If units differ within same SKU/Invoice we stick to the first one found (simplicity)

    # --- Flatten to Template Structure ---
    # groups = [ { "invoice": "...", "items": [...] }, ... ]
    
    final_groups = []
    
    # Sort invoices? Maybe numerical if possible, or string sort.
    sorted_invoices = sorted(aggregated_data.keys())
    
    for inv in sorted_invoices:
        items_map = aggregated_data[inv]
        group_items = []
        
        for sku, data in items_map.items():
            # Breakdown Text
            # If we have box data, show that provided by SP
            if data['total_cajas'] > 0:
                 data['breakdown'] = f"{data['total_cajas']} {data['unidad_cajas']}"
            else:
                 # Fallback to old calc or logic? 
                 # If manual item, maybe calculate? User said "Calculated by SP". 
                 # Let's assume manual items don't have box conversion for now or show "-"
                 # Or we could try to calculate BUT user specifically wanted to use the SP columns.
                 # Let's leave as raw units if no box data.
                 data['breakdown'] = f"{data['qty']} {data['unit']}"
            
            group_items.append(data)
            
        # Sort items by name
        group_items.sort(key=lambda x: x['name'])
        
        final_groups.append({
            "invoice": inv,
            "client_name": invoice_clients.get(inv, ""),
            "line_items": group_items
        })

    return templates.TemplateResponse("logistics/print_dispatch.html", {
        "request": request,
        "log": log,
        "groups": final_groups,
        "now": datetime.now()
    })

@router.get("/api/guides/search")
async def search_guides(
    q: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(LogisticsDispatch)
    
    if q:
        query = query.filter(LogisticsDispatch.document_ref.like(f"%{q}%"))
        
    if date_from:
        try:
            d_from = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(LogisticsDispatch.date >= d_from)
        except: pass
        
    if date_to:
        try:
            d_to = datetime.strptime(date_to, '%Y-%m-%d')
            d_to = d_to.replace(hour=23, minute=59, second=59)
            query = query.filter(LogisticsDispatch.date <= d_to)
        except: pass
        
    # Limit results to avoid overload if no filters
    # User complained about slowness. Limit all searches to 200 for now.
    query = query.order_by(LogisticsDispatch.date.desc()).limit(200)
        
    results = query.all()
        
    results = query.all()
    
    guides = []
    for r in results:
        # Extract clean guide number
        ref_clean = r.document_ref.split('|')[0].strip()
        guides.append({
            "id": r.id,
            "document_ref": r.document_ref,
            "guide_number": ref_clean,
            "date": r.date.strftime('%d/%m/%Y'),
            "client": r.client_destination
        })
        
    return guides

@router.get("/api/consolidated_report")
async def get_consolidated_report(
    guide_ref: Optional[str] = None, # Matches document_ref
    date_from: Optional[str] = None, 
    date_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(LogisticsDispatch)
    
    # 1. Filters
    if guide_ref:
        query = query.filter(LogisticsDispatch.document_ref.like(f"{guide_ref}%"))
        
    if date_from:
        try:
            d_from = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(LogisticsDispatch.date >= d_from)
        except: pass
        
    if date_to:
        try:
            d_to = datetime.strptime(date_to, '%Y-%m-%d')
            # Set to end of day
            d_to = d_to.replace(hour=23, minute=59, second=59)
            query = query.filter(LogisticsDispatch.date <= d_to)
        except: pass
    
    results = query.all()
    
    data = calculate_consolidated_data(results)
    
    return {
        "status": "success",
        "details": data['items'],
        "total_boxes_all": data['grand_total_boxes'],
        "total_weight_all": data['grand_total_weight']
    }

def calculate_consolidated_data(results):
    aggregated_items = {}
    total_guide_boxes = 0.0
    total_guide_weight = 0.0
    
    for dispatch in results:
        # Parse items
        try:
            items = json.loads(dispatch.items_json)
        except: items = []
        
        for item in items:
            sku = item.get('sku') or item.get('item', 'Unknown')
            name = item.get('name') or item.get('item', 'Unknown')
            
            # Identify Invoice per item or from dispatch
            item_invoice = item.get('fact', '').strip()
            if not item_invoice and hasattr(dispatch, 'invoice') and dispatch.invoice:
                item_invoice = dispatch.invoice
            if not item_invoice:
                 item_invoice = "S/F" # Sin Factura

            try: qty = float(item.get('qty', 0))
            except: qty = 0.0
            
            try: boxes = float(item.get('total_cajas', 0))
            except: boxes = 0.0
            
            # Weight Extraction Logic
            weight_per_unit = 0.0
            
            # 1. Regex for KG
            kg_match = re.search(r'(\d+(\.\d+)?)\s*(kg|Kg|KG|kG)', name)
            if kg_match:
                weight_per_unit = float(kg_match.group(1))
            else:
                # 2. Regex for Grams
                g_match = re.search(r'(\d+)\s*(g|gr|G|Gr|GR)', name)
                if g_match:
                    weight_per_unit = float(g_match.group(1)) / 1000.0

            total_weight = qty * weight_per_unit
            
            if sku not in aggregated_items:
                aggregated_items[sku] = {
                    'sku': sku,
                    'name': name,
                    'total_units': 0.0,
                    'total_boxes': 0.0,
                    'total_weight': 0.0,
                    'unit': item.get('unit', 'UNI'),
                    'invoices': set()
                }
            
            aggregated_items[sku]['total_units'] += qty
            aggregated_items[sku]['total_boxes'] += boxes
            aggregated_items[sku]['total_weight'] += total_weight
            aggregated_items[sku]['invoices'].add(item_invoice)
            
            total_guide_boxes += boxes
            total_guide_weight += total_weight

    # Format list
    response_items = []
    for k, v in aggregated_items.items():
        v['invoices'] = sorted(list(v['invoices'])) # Convert set to list
        response_items.append(v)
        
    response_items.sort(key=lambda x: x['name'])
    
    return {
        "items": response_items,
        "grand_total_boxes": round(total_guide_boxes, 2),
        "grand_total_weight": round(total_guide_weight, 4)
    }

@router.get("/consolidated_report/print")
async def view_print_consolidated_report(
    request: Request,
    guide_ref: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(LogisticsDispatch)
    
    if guide_ref:
        query = query.filter(LogisticsDispatch.document_ref.like(f"{guide_ref}%"))
        
    if date_from:
        try:
            d_from = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(LogisticsDispatch.date >= d_from)
        except: pass
        
    if date_to:
        try:
            d_to = datetime.strptime(date_to, '%Y-%m-%d')
            d_to = d_to.replace(hour=23, minute=59, second=59)
            query = query.filter(LogisticsDispatch.date <= d_to)
        except: pass
    
    results = query.all()
    data = calculate_consolidated_data(results)
    
    return templates.TemplateResponse("logistics/print_consolidated.html", {
        "request": request,
        "guide_ref": guide_ref,
        "date_from": date_from,
        "date_to": date_to,
        "items": data['items'],
        "grand_total_boxes": data['grand_total_boxes'],
        "grand_total_weight": data['grand_total_weight'],
        "now": datetime.now()
    })

def generate_next_guide_number(db: Session):
    # Find all refs starting with GUIA-
    last_dispatches = db.query(LogisticsDispatch.document_ref)\
        .filter(LogisticsDispatch.document_ref.like('GUIA-%'))\
        .order_by(LogisticsDispatch.id.desc())\
        .limit(100).all() 
        
    max_num = 0
    for r in last_dispatches:
        try:
            base_ref = r.document_ref.split('|')[0].strip()
            match = re.search(r'GUIA-(\d+)', base_ref)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
        except: pass
        
    next_num = max_num + 1
    return f"GUIA-{next_num:08d}"
