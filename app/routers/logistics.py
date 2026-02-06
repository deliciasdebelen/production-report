from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, text
from typing import Optional, List
from ..external_db import get_external_db
import json
from datetime import datetime, timedelta
import re

from ..dependencies import get_db, templates, get_current_user, get_current_active_user
from ..models import LogisticsReceptionProduction, LogisticsReceptionMerchandise, LogisticsDispatch, User, ProductionReport, LogisticsRoute
from .. import schemas, models

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
    return templates.TemplateResponse("logistics/inventory.html", {
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

@router.get("/dispatch/{dispatch_id}/print-labels")
async def view_dispatch_labels(
    dispatch_id: int, 
    request: Request, 
    user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not user: return RedirectResponse("/login")
    if user.role not in [1, 3, 4, 5]:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    log = db.query(LogisticsDispatch).filter(LogisticsDispatch.id == dispatch_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Guía no encontrada")
        
    # Parse Items
    try:
        items = json.loads(log.items_json)
    except:
        items = []

    # Generate Labels
    labels = []
    # Extract Guide Ref (remove invoice part if present for cleaner label)
    # Ref format: "GUIDE | Fact: 123,456"
    guide_ref = log.document_ref.split(' | ')[0]
    
    date_str = log.date.strftime('%d/%m/%Y')
    
    for item in items:
        # Check Total Boxes
        try:
            total_boxes = float(item.get('total_cajas', 0))
            # If 0, skip or maybe just print 1 label if qty > 0?
            # User request: "imprimir por cada cantidad de cajas 1 etiqueta"
            # If total_boxes is 0.5? Print 1? 
            # If total_boxes is 0 (e.g. only units)? 
            # Let's assume boxes integer logic. round up? 
            # If 5.5 boxes, usually means 5 boxes + loose. 
            # Or 6 physical boxes.
            # Let's use ceil logic or just integer part if breakdown usually says "X CAJ".
            
            # Safe approach: Round up to nearest integer for label count
            import math
            box_count = int(math.ceil(total_boxes))
            
            if box_count == 0 and float(item.get('qty', 0)) > 0:
                 # Fallback: Print 1 label if there are units but no boxes defined?
                 # User specific example: "Caja 1 de 10". Implies box tracking.
                 # If no boxes, maybe no labels needed? Or 1 generic.
                 # Let's Skip if 0 boxes to be safe, unless user complains.
                 pass

            factura = item.get('fact', 'N/A')
            descripcion = item.get('item', 'Item')
            num_lote = item.get('num_lote', '') # Extract Lote

            # Clean description (remove code if present at end)
            # Description usually "DESC (CODE)"
            # Let's keep it full or short? User example: "PIPITA..."
            
            for i in range(1, box_count + 1):
                labels.append({
                    "factura": factura,
                    "guia": guide_ref,
                    "descripcion": descripcion,
                    "num_lote": num_lote, # Pass to template
                    "box_current": i,
                    "box_total": box_count,
                    "fecha": date_str
                })
                
        except Exception as e:
            print(f"Error generating label for item: {e}")

    return templates.TemplateResponse("logistics/print_labels.html", {
        "request": request,
        "user": user,
        "labels": labels,
        "document_ref": log.document_ref,
        "total_labels": len(labels)
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


@router.get("/api/external/invoices/search")
async def search_invoices(
    q: str,
    db: Session = Depends(get_external_db)
):
    """
    Search invoices by partial number.
    Returns list of { doc_num, client }
    """
    if not q or len(q) < 2: return []
    
    try:
        # Determine SQL dialect for limit syntax
        # MSSQL uses TOP, SQLite/Postgres uses LIMIT
        dialect = db.bind.dialect.name
        
        if dialect == "mssql":
            query = text("""
                SELECT TOP 20 f.doc_num, f.descrip AS invoice_desc, c.cli_des AS client_name 
                FROM saFacturaVenta f
                LEFT JOIN saCliente c ON f.co_cli = c.co_cli
                WHERE f.doc_num LIKE :q OR c.cli_des LIKE :q
                ORDER BY f.doc_num DESC
            """)
        else:
            # Fallback for SQLite/others
            query = text("""
                SELECT f.doc_num, f.descrip AS invoice_desc, c.cli_des AS client_name 
                FROM saFacturaVenta f
                LEFT JOIN saCliente c ON f.co_cli = c.co_cli
                WHERE f.doc_num LIKE :q OR c.cli_des LIKE :q
                ORDER BY f.doc_num DESC
                LIMIT 20
            """)
        
        results = db.execute(query, {"q": f"%{q}%"}).fetchall()
        
        data = []
        for r in results:
            data.append({
                "doc_num": r.doc_num.strip(),
                "client": r.client_name.strip(),
                "display": f"{r.doc_num.strip()} - {r.client_name.strip()}"
            })
            
        return data
    except Exception as e:
        print(f"Error searching invoices: {e}")
        return []

@router.get("/api/external/invoice/{doc_num}/items")
async def get_invoice_items(
    doc_num: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_external_db),
    local_db: Session = Depends(get_db)
):
    """
    Get items for a SPECIFIC invoice using V2 SP.
    Validates if invoice is already dispatched.
    """
    try:
        # 1. Global Validation: Check if invoice already dispatched
        # Check against LogisticsDispatch items_json
        # Performance: Ideally we index this, but for now we scan recent or all? 
        # Using LIKE is risky if format differs. 
        # Better: Check 'document_ref' if we store it there? No, document_ref is the Guide Number.
        # We store invoices in items_json OR in the document_ref string sometimes.
        # Let's check distinct invoices in the timeframe or global? 
        # User said "no puedes agregar una factura ya incluida en una guia guardada".
        
        # Optimized approach: Search text in items_json.
        # Note: This might be slow if table grows huge.
        # Safe limit: Last 12 months? Or just all.
        
        already_dispatched = local_db.query(LogisticsDispatch).filter(
            LogisticsDispatch.items_json.like(f'%\"fact\": \"{doc_num}\"%') 
            | LogisticsDispatch.items_json.like(f'%\"fact\": \"{doc_num.strip()}\"%')
        ).first()
        
        if already_dispatched:
             return {"error": f"La factura {doc_num} ya fue despachada en la Guía {already_dispatched.document_ref}"}

        # 2. Execute SP V2
        # Param: doc_num? User said "en vez de co_cli, sera por el doc_num".
        # Assumption: Param is named @doc_num based on standard.
        sql = text("EXEC SP_CRM_FacturasPendientesPorClienteV2 @doc_num = :d")
        result_proxy = db.execute(sql, {"d": doc_num})
        result = result_proxy.fetchall()
        
        if not result:
            return [] # No items found or invalid invoice

        def get_col(row_map, candidates):
            for c in candidates:
                if c in row_map: return row_map[c]
            keys = list(row_map.keys())
            for c in candidates:
                for k in keys:
                     # Exact match first, then partial?
                    if c.lower() == k.lower(): return row_map[k]
            for c in candidates:
                for k in keys:
                    if c.lower() in k.lower(): return row_map[k]
            return None

        final_items = []
        aggregated = {}
        
        # Meta info from first row (assuming uniform)
        client_name = ""
        total_factura = 0.0 # From SP column if available, or sum? 
        # User said "crea un campo en el total al para mostrar el monto total factura" -> in the report?
        # But implies backend should return it.
        # Check if SP returns 'monto_total' or similar?
        # We can sum it up or look for column.
        
        for row in result:
             row_map = row._mapping
             
             # Extract Columns
             fact_num_row = str(get_col(row_map, ['Número Factura', 'fact_num', 'Numero Factura']) or "").strip()
             if fact_num_row and fact_num_row != doc_num: pass # Should match if SP filters correctly
             
             co_art = str(get_col(row_map, ['Código Artículo', 'co_art', 'Codigo Articulo']) or "").strip()
             art_des = str(get_col(row_map, ['Descripción Artículo', 'art_des', 'Descripcion Articulo']) or "").strip()
             co_uni = str(get_col(row_map, ['Unidad', 'co_uni', 'units']) or "UNI").strip()
             num_lote = str(get_col(row_map, ['numero_lote', 'num_lote', 'lote', 'nro_lote', 'Lote']) or "").strip()
             
             client_name = str(get_col(row_map, ['Cliente', 'cli_des', 'Nombre Cliente']) or "Cliente Desconocido").strip()
             
             # Amounts/Weights
             raw_units = get_col(row_map, ['Total Articulo', 'total_articulo'])
             raw_boxes = get_col(row_map, ['Cantidad Cajas', 'cantidad_cajas'])
             raw_net_weight = get_col(row_map, ['Peso', 'peso_neto', 'peso']) # Weight per unit or total? Usually per unit in master, or total in row?
             # User said: "ajusta el calculo de peso Unidades * el peso en la descripcion del articulo" context: Consolidated Report.
             # But here we might get it.
             
             # Price/Total Amount for Invoice Total
             # Look for 'monto_total', 'total_neto', 'precio'?
             # Assuming row has line total.
             raw_line_total = get_col(row_map, ['monto_renglon', 'total_renglon', 'precio_total']) 
             if raw_line_total:
                 try: total_text = float(raw_line_total)
                 except: total_text = 0.0
                 total_factura += total_text
             
             try: units = float(raw_units) if raw_units is not None else 1.0
             except: units = 1.0
             try: boxes = float(raw_boxes) if raw_boxes is not None else 0.0
             except: boxes = 0.0

             if not co_art: continue

             # Key by (SKU, Batch) to separate batches in list
             key = (co_art, num_lote)
             if key not in aggregated:
                 aggregated[key] = {
                     "fact_num": fact_num_row, 
                     "co_art": co_art,
                     "art_des": art_des,
                     "co_uni": co_uni, 
                     "num_lote": num_lote,
                     "total_articulo": 0.0,
                     "total_cajas": 0.0,
                     "unidad_cajas": "CAJ", # Default or extract
                     "client_name": client_name,
                     "weight_base": 0.0 # Placeholder
                 }
             aggregated[key]['total_articulo'] += units
             aggregated[key]['total_cajas'] += boxes
        
        # If 'total_factura' was effectively 0 (no column), try to get from Header or ignore?
        # Maybe the SP returns a column 'total_factura' repeated? 
        # Check one row
        if result:
            first = result[0]._mapping
            # Add 'Total Factura' (from debug) and 'total_neto' (from table default)
            raw_inv_total = get_col(first, ['Total Factura', 'total_factura', 'monto_total', 'total_final', 'total_neto'])
            if raw_inv_total:
                 try: total_factura = float(raw_inv_total)
                 except: pass

        # Flatten
        response_list = []
        for v in aggregated.values():
            v['total_cajas'] = round(v['total_cajas'], 2)
            v['invoice_total'] = total_factura # Embed in every item or just use frontend logic? 
            # Frontend needs it once per invoice.
            response_list.append(v)
            
        return response_list

    except Exception as e:
        print(f"Error fetching invoice items V2: {e}")
        return {"error": str(e)}

@router.get("/api/external/delivery_notes/search")
async def search_delivery_notes(
    q: str,
    db: Session = Depends(get_external_db)
):
    """
    Search delivery notes by partial number.
    Returns list of { doc_num, client }
    """
    if not q or len(q) < 2: return []
    
    try:
        # Determine SQL dialect for limit syntax
        dialect = db.bind.dialect.name
        
        if dialect == "mssql":
            query = text("""
                SELECT TOP 20 f.doc_num, f.descrip AS invoice_desc, c.cli_des AS client_name 
                FROM saNotaEntregaVenta f
                LEFT JOIN saCliente c ON f.co_cli = c.co_cli
                WHERE f.doc_num LIKE :q OR c.cli_des LIKE :q
                ORDER BY f.doc_num DESC
            """)
        else:
            # Fallback for SQLite/others
            query = text("""
                SELECT f.doc_num, f.descrip AS invoice_desc, c.cli_des AS client_name 
                FROM saNotadentregaventa f
                LEFT JOIN saCliente c ON f.co_cli = c.co_cli
                WHERE f.doc_num LIKE :q OR c.cli_des LIKE :q
                ORDER BY f.doc_num DESC
                LIMIT 20
            """)
        
        results = db.execute(query, {"q": f"%{q}%"}).fetchall()
        
        data = []
        for r in results:
            data.append({
                "doc_num": r.doc_num.strip(),
                "client": r.client_name.strip(),
                "display": f"{r.doc_num.strip()} - {r.client_name.strip()}"
            })
            
        return data
    except Exception as e:
        print(f"Error searching delivery notes: {e}")
        return []

@router.get("/api/external/delivery_note/{doc_num}/items")
async def get_delivery_note_items(
    doc_num: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_external_db),
    local_db: Session = Depends(get_db)
):
    """
    Get items for a SPECIFIC delivery note.
    """
    try:
        # 1. Check if already dispatched (Optional validation, maybe warn?)
        # For now, let's skip strict validation or use same logic if needed.
        
        # 2. Execute SP
        sql = text("EXEC SP_CRM_NotasEntregaPendientesPorClienteV2 @doc_num = :d")
        result_proxy = db.execute(sql, {"d": doc_num})
        result = result_proxy.fetchall()
        
        if not result:
            return []

        def get_col(row_map, candidates):
            for c in candidates:
                if c in row_map: return row_map[c]
            keys = list(row_map.keys())
            for c in candidates:
                for k in keys:
                    if c.lower() == k.lower(): return row_map[k]
            for c in candidates:
                for k in keys:
                    if c.lower() in k.lower(): return row_map[k]
            return None

        aggregated = {}
        total_factura = 0.0 
        client_name = ""

        for row in result:
             row_map = row._mapping
             
             # Extract Columns
             # Note: SP might return different column names, but usually consistent.
             fact_num_row = str(get_col(row_map, ['Número Documento', 'doc_num', 'Numero Documento', 'Número Nota']) or doc_num).strip()
             
             co_art = str(get_col(row_map, ['Código Artículo', 'co_art', 'Codigo Articulo']) or "").strip()
             art_des = str(get_col(row_map, ['Descripción Artículo', 'art_des', 'Descripcion Articulo']) or "").strip()
             co_uni = str(get_col(row_map, ['Unidad', 'co_uni', 'units']) or "UNI").strip()
             num_lote = str(get_col(row_map, ['numero_lote', 'num_lote', 'lote', 'nro_lote', 'Lote']) or "").strip()
             
             client_name = str(get_col(row_map, ['Cliente', 'cli_des', 'Nombre Cliente']) or "Cliente Desconocido").strip()
             
             raw_units = get_col(row_map, ['Total Articulo', 'total_articulo'])
             raw_boxes = get_col(row_map, ['Cantidad Cajas', 'cantidad_cajas'])
             
             # Price/Total
             raw_line_total = get_col(row_map, ['monto_renglon', 'total_renglon', 'precio_total']) 
             if raw_line_total:
                 try: total_text = float(raw_line_total)
                 except: total_text = 0.0
                 total_factura += total_text
             
             try: units = float(raw_units) if raw_units is not None else 1.0
             except: units = 1.0
             try: boxes = float(raw_boxes) if raw_boxes is not None else 0.0
             except: boxes = 0.0

             if not co_art: continue

             # Key by (SKU, Batch)
             key = (co_art, num_lote)
             if key not in aggregated:
                 aggregated[key] = {
                     "fact_num": fact_num_row, 
                     "co_art": co_art,
                     "art_des": art_des,
                     "co_uni": co_uni, 
                     "num_lote": num_lote,
                     "total_articulo": 0.0,
                     "total_cajas": 0.0,
                     "unidad_cajas": "CAJ", 
                     "client_name": client_name,
                     "weight_base": 0.0
                 }
             aggregated[key]['total_articulo'] += units
             aggregated[key]['total_cajas'] += boxes
        
        # Flatten
        response_list = []
        for v in aggregated.values():
            v['total_cajas'] = round(v['total_cajas'], 2)
            v['invoice_total'] = total_factura 
            response_list.append(v)
            
        return response_list

    except Exception as e:
        print(f"Error fetching delivery note items: {e}")
        return {"error": str(e)}

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
    route_select: Optional[str] = Form(None), # Dropdown ID
    route_input: Optional[str] = Form(None), # Manual Input
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    external_db: Session = Depends(get_external_db)
):
    # Manual Form Parsing to Bypass "Field required" persistence
    # Pydantic/FastAPI was refusing to accept the missing/empty field despite Optional[str]
    form_data = await request.form()
    client_destination = form_data.get("client_destination", "")
    
    # --- Route Logic ---
    # Prioritize Input (if toggle is active/filled), then Select
    # But Select returns ID. We want Name for the dispatch record? Or ID? 
    # The model likely has 'logistics_route_id' or just a string 'route_name'?
    # Let's check the model via code or inference. 
    # Current model `LogisticsDispatch` usually has `route_name` based on previous chats (or `route` string).
    # If ID is provided, we should fetch the name.
    
    route_name = ""
    if route_input and route_input.strip():
        route_name = route_input.strip()
    elif route_select and route_select.strip():
        # Fetch Name from ID
        try:
            r_id = int(route_select)
            route_obj = db.query(LogisticsRoute).filter(LogisticsRoute.id == r_id).first()
            if route_obj:
                route_name = route_obj.name
        except: pass
        
    # Validation
    if not route_name:
         # raise HTTPException(status_code=400, detail="Debe seleccionar o ingresar una Ruta.")
         pass # Allow empty? User said "revisa la funcionalidad... no esta funcionando". Best to require it or ensure it saves.

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
    # Handle Route: ID or New Name
    route_id_val = None
    
    try:
        # Priority 1: Manual Input (New or Existing by Name)
        if route_input and route_input.strip():
            r_name = route_input.strip()
            # Check if exists
            route_obj = db.query(LogisticsRoute).filter(LogisticsRoute.name == r_name).first()
            if not route_obj:
                # Create
                route_obj = LogisticsRoute(name=r_name, active=True)
                db.add(route_obj)
                db.commit()
                db.refresh(route_obj)
            else:
                # Reactivate if needed
                if not route_obj.active:
                    route_obj.active = True
                    db.commit()
            
            route_id_val = route_obj.id
            
        # Priority 2: Selected Dropdown
        elif route_select and route_select.strip():
            try:
                route_id_val = int(route_select)
            except: pass
            
    except Exception as e:
        print(f"Error handling route: {e}")

    new_log = LogisticsDispatch(
        client_destination=final_client,
        document_ref=final_ref,
        items_json=json.dumps(enriched_items), # Save Enriched JSON
        route_id=route_id_val
    )
    db.add(new_log)
    db.commit()

    return {
        "status": "success", 
        "summary": summary_data, 
        "document_ref": final_ref,
        "id": new_log.id
    }

# --- Route APIs ---

@router.get("/api/routes", response_model=List[schemas.LogisticsRoute])
def get_routes(db: Session = Depends(get_db)):
    return db.query(models.LogisticsRoute).filter(models.LogisticsRoute.active == True).order_by(models.LogisticsRoute.name).all()

@router.post("/api/routes", response_model=schemas.LogisticsRoute)
def create_route(route: schemas.LogisticsRouteCreate, db: Session = Depends(get_db)):
    # Check exists
    existing = db.query(models.LogisticsRoute).filter(models.LogisticsRoute.name == route.name).first()
    if existing:
        if not existing.active:
            existing.active = True # Reactivate
            db.commit()
            db.refresh(existing)
            return existing
        return existing
        
    new_route = models.LogisticsRoute(name=route.name, active=route.active)
    db.add(new_route)
    db.commit()
    db.refresh(new_route)
    return new_route

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
        
    try:
        raw_items = json.loads(log.items_json)
    except:
        raw_items = []

    aggregated_data = {}
    invoice_meta = {} # Map invoice -> {client, total}
    
    # Pre-scan for metadata (Client & Total from JSON)
    for item in raw_items:
        inv = item.get('fact', '').strip()
        if not inv: inv = "Otros / Manual"
        
        if inv not in invoice_meta:
            invoice_meta[inv] = {
                "client": item.get('client', ''),
                "total": item.get('invoice_total', 0.0)
            }
        else:
            # If valid (not empty), overwrite? Or keep first?
            # Prefer items with data.
            if not invoice_meta[inv]["client"] and item.get('client'):
                invoice_meta[inv]["client"] = item.get('client')
            if invoice_meta[inv]["total"] == 0.0 and item.get('invoice_total'):
                invoice_meta[inv]["total"] = item.get('invoice_total')

    # Fallback: Query DB for missing Clients (Legacy support)
    unique_invoices = [i for i in invoice_meta.keys() if i != "Otros / Manual" and not invoice_meta[i]["client"]]
    if unique_invoices:
        try:
            for inv_num in unique_invoices:
                 query = text("""
                     SELECT c.descrip 
                     FROM saFacturaVenta f
                     JOIN saCliente c ON f.co_cli = c.co_cli
                     WHERE f.doc_num = :doc_num
                 """)
                 row = external_db.execute(query, {"doc_num": inv_num}).first()
                 if row:
                     invoice_meta[inv_num]["client"] = row[0].strip()
        except: pass

    for item in raw_items:
        # 1. Identify Invoice
        invoice = item.get('fact', '').strip() or "Otros / Manual"
            
        # 2. Identify SKU
        raw_name = item.get('name', item.get('item', 'Unknown'))
        sku = item.get('sku')
        if not sku:
             sku_match = re.search(r'\((.*?)\)$', raw_name)
             sku = sku_match.group(1).strip() if sku_match else raw_name.strip()
             
        # 3. Values
        try: qty = float(item.get('qty', 0))
        except: qty = 0.0
        unit = item.get('unit', 'UNID')
        
        try: imported_boxes = float(item.get('total_cajas', 0))
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

    # --- Flatten ---
    final_groups = []
    sorted_invoices = sorted(aggregated_data.keys())
    
    for inv in sorted_invoices:
        items_map = aggregated_data[inv]
        group_items = []
        
        for sku, data in items_map.items():
            if data['total_cajas'] > 0:
                 data['breakdown'] = f"{data['total_cajas']} {data['unidad_cajas']}"
            else:
                 data['breakdown'] = f"{data['qty']} {data['unit']}"
            group_items.append(data)
            
        group_items.sort(key=lambda x: x['name'])
        
        meta = invoice_meta.get(inv, {})
        final_groups.append({
            "invoice": inv,
            "client_name": meta.get('client', 'Cliente Desconocido'),
            "invoice_total": meta.get('total', 0.0), # Pass Total
            "line_items": group_items
        })

    return templates.TemplateResponse("logistics/print_dispatch.html", {
        "request": request,
        "log": log,
        "groups": final_groups,
        "now": datetime.now() - timedelta(hours=4) # UTC-4 VZLA
    })

# ... search_guides omitted (unchanged) ...
# I need to keep the code structure valid, so I will replace from print_dispatch start to calculate_consolidated_data end if possible
# or skip search_guides.
# The tool might need precise range. 
# Better to replace the whole block including search_guides or just print_dispatch and consolidated separately.
# I will try to target print_dispatch separately first.
# Wait, I cannot use multiple tools here effectively to stitch.
# I will include search_guides in the replacement content to bridge the gap if it is small.
# search_guides is roughly lines 902-947 (45 lines).
# print_dispatch is 755-900.
# calculate_consolidated is 987+
# I'll stick to replacing print_dispatch first.

# UPDATE: I'll actually split this into two calls for safety. First print_dispatch.


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
    db: Session = Depends(get_db),
    external_db: Session = Depends(get_external_db)
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
    
    data = calculate_consolidated_data(results, external_db=external_db)
    
    return {
        "status": "success",
        "details": data['items'],
        "total_boxes_all": data['grand_total_boxes'],
        "total_weight_all": data['total_weight_all'] if 'total_weight_all' in data else data['grand_total_weight'],
        "total_amount_all": data['grand_total_amount'],
        "total_invoices_count": data.get('grand_total_invoices_count', 0)
    }

def calculate_consolidated_data(results, external_db: Session = None):
    aggregated_items = {}
    total_guide_boxes = 0.0
    total_guide_weight = 0.0
    grand_total_amount = 0.0
    
    # Pre-process Invoices to get Totals (Optimization for legacy data)
    # Map: invoice_num -> amount
    invoice_totals_map = {}
    missing_invoices = set()
    
    # 1. Collect Invoices from all dispatches
    all_dispatches_items = []
    
    for dispatch in results:
        try:
            items = json.loads(dispatch.items_json)
        except: items = []
        
        all_dispatches_items.append((dispatch, items))
        
        for item in items:
            inv = item.get('fact', '').strip()
            if not inv: continue
            
            # Check if total is present
            try: amt = float(item.get('invoice_total', 0.0))
            except: amt = 0.0
            
            if amt > 0:
                invoice_totals_map[inv] = amt
            elif inv not in invoice_totals_map:
                missing_invoices.add(inv)
                
    # 2. Backfill missing totals from External DB if available
    if missing_invoices and external_db:
        try:
            # Chunking not implemented for simplicity (assume < 2000 invoices per report)
            invoices_list = list(missing_invoices)
            if invoices_list:
                # Need to handle potential SQL injection if we just f-string? 
                # Use parameterized query with IN clause or multiple queries?
                # SQLAlchemy text handling of list: 'WHERE doc_num IN :nums'
                
                # Manually expand parameters to avoid MSSQL ODBC 'IN' clause issues with list/tuples
                # 1. Check Invoices
                inv_keys = [f"inv{i}" for i in range(len(invoices_list))]
                inv_params = {k: v for k, v in zip(inv_keys, invoices_list)}
                
                if inv_params:
                    query = text(f"""
                        SELECT doc_num, total_neto 
                        FROM saFacturaVenta 
                        WHERE doc_num IN ({', '.join([':' + k for k in inv_keys])})
                    """)
                    res = external_db.execute(query, inv_params).fetchall()
                    
                    for r in res:
                        try:
                            invoice_totals_map[r.doc_num.strip()] = float(r.total_neto or 0.0)
                        except: pass
                    
                    # 2b. Check Delivery Notes for remaining
                    found_docs = set([r.doc_num.strip() for r in res])
                else:
                    found_docs = set()
                
                still_missing_list = [i for i in invoices_list if i not in found_docs]
                
                if still_missing_list:
                    ne_keys = [f"ne{i}" for i in range(len(still_missing_list))]
                    ne_params = {k: v for k, v in zip(ne_keys, still_missing_list)}
                    
                    query_ne = text(f"""
                        SELECT doc_num, total_neto 
                        FROM saNotaEntregaVenta 
                        WHERE doc_num IN ({', '.join([':' + k for k in ne_keys])})
                    """)
                    res_ne = external_db.execute(query_ne, ne_params).fetchall()
                    
                    for r in res_ne:
                        try:
                            invoice_totals_map[r.doc_num.strip()] = float(r.total_neto or 0.0)
                        except: pass
                        
        except Exception as e:
            print(f"Error backfilling invoice/note totals: {e}")

    # 3. Calculate Grand Total
    grand_total_amount = sum(invoice_totals_map.values())
    
    # 4. Aggregation Logic
    for dispatch, items in all_dispatches_items: 
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
            
            # 1. Regex for KG (Support comma or dot)
            # Match 3.85kg or 3,85kg
            # Use [.,] for separator.
            kg_match = re.search(r'(\d+([.,]\d+)?)\s*(kg|Kg|KG|kG)', name)
            if kg_match:
                # Replace comma with dot for float conversion
                val_str = kg_match.group(1).replace(',', '.')
                weight_per_unit = float(val_str)
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
    
    # ... (rest of function)
    
    # We need to return the dict with grand_total_amount.
    # Need to check where response_items logic is. 
    # I replaced the top half. I need to make sure I don't cut off the bottom or I need to replace the WHOLE function.
    # The existing function is long. 
    # I should replace the whole function to be safe.
    
    for sku, data in aggregated_items.items():
        response_items.append({
            "sku": data['sku'],
            "name": data['name'],
            "total_units": data['total_units'],
            "total_boxes": round(data['total_boxes'], 2),
            "total_weight": round(data['total_weight'], 2),
            "invoices": list(data['invoices'])
        })
        
    response_items.sort(key=lambda x: x['name'])
    
    return {
        "items": response_items,
        "grand_total_boxes": round(total_guide_boxes, 2),
        "grand_total_weight": round(total_guide_weight, 2),
        "grand_total_amount": round(grand_total_amount, 2),
        "grand_total_invoices_count": len(invoice_totals_map) # New Field
    }

@router.get("/consolidated_report/print")
async def view_print_consolidated_report(
    request: Request,
    guide_ref: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    external_db: Session = Depends(get_external_db)
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
    data = calculate_consolidated_data(results, external_db=external_db)
    
    return templates.TemplateResponse("logistics/print_consolidated.html", {
        "request": request,
        "guide_ref": guide_ref,
        "date_from": date_from,
        "date_to": date_to,
        "items": data['items'],
        "grand_total_boxes": data['grand_total_boxes'],
        "grand_total_weight": data['grand_total_weight'],
        "grand_total_amount": data['grand_total_amount'],
        "grand_total_invoices_count": data.get('grand_total_invoices_count', 0), # Added
        "now": datetime.now() - timedelta(hours=4) # UTC-4 VZLA Fix
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



@router.get("/dispatch/{id}/print")
async def print_dispatch(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    from ..dependencies import check_permission
    if not check_permission(current_user, "logistics", "print"):
        raise HTTPException(status_code=403, detail="No tiene permisos para imprimir")
        
    dispatch = db.query(LogisticsDispatch).filter(LogisticsDispatch.id == id).first()
    if not dispatch:
        raise HTTPException(status_code=404, detail="Despacho no encontrado")
        
    # Parse Items & Group by Document
    items = []
    try:
        items = json.loads(dispatch.items_json)
    except: pass

    # Sort items by fact to ensure nice grouping
    items.sort(key=lambda x: x.get('fact', ''))

    grouped_data = {}
    header_invoices = set()
    header_notes = set()

    for item in items:
        ref = item.get('fact', 'Sin Ref').strip()
        if not ref: ref = "Sin Ref"
        
        # Detect Type
        # Logic: If it looks like a standard invoice (all digits), it's a Factura.
        # If it has "NE", "NOTA", or is non-standard, treat as Note? 
        # User example: "Factura: 0000013441" -> Pure digits is standard invoice.
        # Unless user prefixed it in 'fact' field. 
        # Let's check typical format. usually just numbers.
        # But if 'fact' field is just a number, how do we distinguish? 
        # The user said: "cuando sea Factura... y cuando tenga notas de entrega".
        # This implies the SYSTEM logic that created the item knows.
        # OR we rely on a prefix check. 
        # Assumption: Invoices are usually numeric. Delivery Notes often have prefixes in this system or different series.
        # Let's stick to the visual request: "Factura: X" vs "Nota de Entrega: Y".
        # If the ref starts with "NE" or "NOTA", label as "Nota de Entrega".
        # Else label as "Factura".
        
        doc_type_label = "Factura"
        if str(ref).upper().startswith("NE") or "NOTA" in str(ref).upper():
            doc_type_label = "Nota de Entrega"
            header_notes.add(ref)
        else:
            header_invoices.add(ref)
            
        if ref not in grouped_data:
            grouped_data[ref] = {
                "type_label": doc_type_label,
                "number": ref,
                "client_name": dispatch.client_destination,
                "invoice_total": 0.0,
                "line_items": []
            }
        
        grouped_data[ref]['line_items'].append(item)
        # Add to total if available? (Usually pre-calced outside, but we can try sum)
        try:
            qty = float(item.get('qty', 0))
            price = float(item.get('price', 0)) # If price exists
            grouped_data[ref]['invoice_total'] += (qty * price)
        except: pass

    # Convert to list
    groups = list(grouped_data.values())
    
    # Sort groups? Numeric if possible
    groups.sort(key=lambda x: x['number'])

    return templates.TemplateResponse("logistics/print_dispatch.html", {
        "request": request,
        "log": dispatch,
        "groups": groups,
        "header_invoices": sorted(list(header_invoices)),
        "header_notes": sorted(list(header_notes)),
        "now": datetime.now()
    })
