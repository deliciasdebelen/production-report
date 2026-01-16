from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..external_db import get_external_db, get_manufacturing_db
from ..models import User
from ..dependencies import get_current_active_user # Correct import now
from typing import Optional
from datetime import datetime

router = APIRouter(
    prefix="", # We will use specific prefixes per route group or root for pages
    tags=["traslados"]
)

templates = Jinja2Templates(directory="app/templates")

def check_role(user: User):
    if user.role not in [2, 4]: # 2=Prod, 4=Admin
        raise HTTPException(status_code=403, detail="Not authorized")

@router.get("/traslados", response_class=HTMLResponse)
async def view_traslados(request: Request, user: User = Depends(get_current_active_user)):
    if user.role not in [2, 4]: # Allow 2 and 4
         return templates.TemplateResponse("403.html", {"request": request, "user": user})
    return templates.TemplateResponse("traslados.html", {"request": request, "title": "Traslados", "user": user})

@router.get("/traslados/tiempo-real", response_class=HTMLResponse)
async def view_traslados_realtime(request: Request, user: User = Depends(get_current_active_user)):
    if user.role not in [2, 4]:
         return templates.TemplateResponse("403.html", {"request": request, "user": user})
    return templates.TemplateResponse("traslados-tiempo-real.html", {"request": request, "title": "Traslados en Tiempo Real", "user": user})

@router.get("/traslados/facturas", response_class=HTMLResponse)
async def view_traslados_facturas(request: Request, user: User = Depends(get_current_active_user)):
    if user.role not in [2, 4]:
         return templates.TemplateResponse("403.html", {"request": request, "user": user})
    return templates.TemplateResponse("traslados-facturas.html", {"request": request, "title": "Facturas Pendientes", "user": user})


# --- APIs ---

@router.get("/api/traslados/almacenes")
def api_almacenes(user: User = Depends(get_current_active_user), db: Session = Depends(get_external_db)):
    try:
        # RepAlmacen is a stored procedure or query.
        # CRM_BELEN: cursor.execute("EXEC RepAlmacen")
        sql = text("EXEC RepAlmacen")
        result = db.execute(sql).fetchall()
        
        data = []
        for row in result:
            # RowProxy access: row.co_alma, row.des_alma
            # CRM_BELEN: row['co_alma']
            # SQLAlchemy mapping depends on driver but usually accessible by name
            data.append({
                'codigo': str(row.co_alma).strip(),
                'nombre': str(row.des_alma).strip()
            })
        return data
    except Exception as e:
        print(f"Error /api/traslados/almacenes: {e}")
        return []

@router.get("/api/traslados/cabecera")
def api_traslados_cabecera(
    alm_dest: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_external_db)
):
    try:
        # Normalize params for SQL Server
        # CRM_BELEN passes None if empty string.
        dest = alm_dest if alm_dest else None
        f_from = datetime.strptime(fecha_desde, '%Y-%m-%d').date() if fecha_desde else None
        f_to = datetime.strptime(fecha_hasta, '%Y-%m-%d').date() if fecha_hasta else None

        # SP expects parameters.
        # Using simple string formatting or checking how sqlalchemy handles NULL params in EXEC
        # safely parameterizing is better.
        # Note: SQL Server EXEC syntax with named params: EXEC SP @p1=:p1...
        # Or just ordinal if driver supports.
        
        # Using raw connection cursor might be safer for SPs with complex parameters if SQLAlchemy acts up,
        # but let's try text() with parameters.
        
        sql = text("EXEC SP_CRM_TRASLADOS_CABECERA :alm, :f1, :f2")
        result = db.execute(sql, {"alm": dest, "f1": f_from, "f2": f_to}).fetchall()

        data = []
        for row in result:
             # Map keys. CRM_BELEN: NumeroTraslado, Fecha, AlmacenOrigen, AlmacenDestino, Confirmado, CantidadArticulos
             # We need to ensure we match the template expectations: 
             # columns: "NumeroTraslado", "Fecha", "AlmacenOrigen", ...
             # We trust the SP returns these column names.
             # SQLAlchemy result rows are KeyedTuple, so row.Name works.
             data.append({
                 "NumeroTraslado": row.NumeroTraslado,
                 "Fecha": row.Fecha.strftime('%Y-%m-%d') if row.Fecha else None,
                 "AlmacenOrigen": row.AlmacenOrigen,
                 "AlmacenDestino": row.AlmacenDestino,
                 "Confirmado": row.Confirmado,
                 "CantidadArticulos": row.CantidadArticulos
             })
        return data

    except Exception as e:
        print(f"Error /api/traslados/cabecera: {e}")
        return []

@router.get("/api/traslados/detalle")
def api_traslados_detalle(
    tras_num: Optional[str] = None,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_external_db)
):
    try:
        if not tras_num: return []
        
        sql = text("EXEC SP_CRM_TRASLADOSENTREALMACEN :tras_num")
        result = db.execute(sql, {"tras_num": tras_num}).fetchall()
        
        data = []
        for row in result:
            # CRM_BELEN Template columns: NroLote, Fecha, AlmacenOrigen, AlmacenDestino, CodigoArticulo, DescripcionArticulo, Confirmado
            # SP returns: NroLote, Fecha, AlmOrig, AlmDest, co_art, art_des, Confirma ... ?
            # CRM_BELEN app.py mapped: dict(zip(columns, row)).
            # We assume SP column aliases match what CRM_BELEN expects OR we need to verify.
            # CRM_BELEN app.py just dumps the dict.
            # Template JS: { "data": "NroLote" }, { "data": "CodigoArticulo" }... (CamelCase in JS?)
            # Wait, CRM_BELEN app.py line 177: item = dict(zip(columns, row)).
            # CRM_BELEN traslados.html line 264: { "data": "NroLote" }.
            # So the SP must return "NroLote".
            
            # Note: SQLAlchemy Row._mapping can be converted to dict.
            d = dict(row._mapping) 
            # Handle date formatting
            if 'Fecha' in d and d['Fecha']:
                 d['Fecha'] = d['Fecha'].strftime('%Y-%m-%d')
            data.append(d)
            
        return data

    except Exception as e:
        print(f"Error /api/traslados/detalle: {e}")
        return []

@router.get("/api/traslados/tiempo-real")
def api_traslados_realtime(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_external_db)
):
    try:
        # Logic from CRM_BELEN/app.py api_traslados_tiempo_real
        sql_query = """
            SELECT
                T.tras_num AS NumeroTraslado,
                CAST(T.fecha AS DATE) AS Fecha,
                T.alm_orig AS AlmacenOrigen,
                T.alm_dest AS AlmacenDestino,
                'NO' AS Confirmado,
                COUNT(TR.tras_num) AS CantidadArticulos
            FROM saTraslado AS T
            INNER JOIN saTrasladoReng AS TR ON TR.tras_num = T.tras_num
            WHERE T.anulado = 0 AND T.confirma = 0
            GROUP BY T.tras_num, T.fecha, T.alm_orig, T.alm_dest
            ORDER BY T.tras_num
        """
        result = db.execute(text(sql_query)).fetchall()
        
        data = []
        for row in result:
             data.append({
                 "NumeroTraslado": row.NumeroTraslado,
                 "Fecha": row.Fecha.strftime('%Y-%m-%d') if row.Fecha else None,
                 "AlmacenOrigen": row.AlmacenOrigen,
                 "AlmacenDestino": row.AlmacenDestino,
                 "Confirmado": row.Confirmado,
                 "CantidadArticulos": row.CantidadArticulos
             })
        return data

    except Exception as e:
        print(f"Error /api/traslados/tiempo-real: {e}")
        return []

@router.get("/api/traslados/facturas-pendientes")
def api_facturas_pendientes(
    days: int = Query(15),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_external_db)
):
    try:
        # SP takes no parameters
        sql = text("EXEC SP_CRM_FacturasPendientesGeneral")
        result = db.execute(sql).fetchall()
        
        data = []
        today = datetime.now()
        
        for row in result:
            d = dict(row._mapping)
            
            # Parse Date (SP returns 'dd/mm/yyyy' string or datetime?)
            # Debug output showed: '17/11/2025' (String)
            f_emis_str = d.get('Fecha Emisión', '')
            f_emis_dt = None
            try:
                # Try parsing DD/MM/YYYY
                f_emis_dt = datetime.strptime(str(f_emis_str).strip(), '%d/%m/%Y')
            except:
                pass # Keep None

            # Filter by Aging (Antigüedad)
            aging_days = 0
            if f_emis_dt:
                aging_days = (today - f_emis_dt).days
            
            # Filter logic: Show invoices matching at least user request logic?
            # User said: "select pending invoices for 15, 30, 45, or 60 days"
            # Usually means "Older than X days".
            if aging_days < days:
                continue

            # Map to Frontend Keys
            item = {
                "Numero": str(d.get('Número Factura', '')).strip(),
                "Fecha": f_emis_dt.strftime('%Y-%m-%d') if f_emis_dt else f_emis_str,
                "Cliente": str(d.get('Nombre Cliente', '')).strip(),
                "Vendedor": "-", # Not returned by SP
                "Monto": float(d.get('Total Factura', 0) or 0),
                "Vencimiento": "-", # Not returned by SP
                "DiasVencidos": aging_days
            }
            data.append(item)
            
        return data
    except Exception as e:
        print(f"Error /api/traslados/facturas-pendientes: {e}")
        return []

@router.get("/api/traslados/cierres-manufactura")
def api_cierres_manufactura(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_manufacturing_db)
):
    try:
        # User requested: SELECT odp_num, fec_emis, cie_num FROM NSPCierreOP WHERE aju_num IS NULL
        # assuming 'carmal_m' context or default DB has NSPCierreOP
        sql = text("SELECT odp_num, fec_emis, cie_num FROM NSPCierreOP WHERE aju_num IS NULL")
        result = db.execute(sql).fetchall()
        
        data = []
        for row in result:
             data.append({
                 "odp_num": row.odp_num,
                 "fec_emis": row.fec_emis.strftime('%Y-%m-%d') if row.fec_emis else None,
                 "cie_num": row.cie_num
             })
        return data

    except Exception as e:
        print(f"Error /api/traslados/cierres-manufactura: {e}")
        return []

@router.get("/traslados/ordenes-cierre", response_class=HTMLResponse)
async def view_traslados_ordenes_cierre(request: Request, user: User = Depends(get_current_active_user)):
    if user.role not in [2, 4]:
         return templates.TemplateResponse("403.html", {"request": request, "user": user})
    return templates.TemplateResponse("traslados-ordenes-cierre.html", {"request": request, "title": "Órdenes sin Cierre", "user": user})

@router.get("/api/traslados/ordenes-cierre-pendientes")
def api_ordenes_cierre_pendientes(
    days: int = Query(15),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_manufacturing_db)
):
    try:
        sql = text("SELECT odp_num, fec_emis, cie_num FROM NSPCierreOP WHERE aju_num IS NULL")
        result = db.execute(sql).fetchall()
        
        data = []
        today = datetime.now()
        
        for row in result:
            # Map Row
            d = dict(row._mapping)
            
            # Parse Date
            f_emis_dt = d.get('fec_emis') # SQLAlchemy usually returns datetime/date object for SQL Server DATE/DATETIME
            
            # Filter by Aging
            aging_days = 0
            if f_emis_dt:
                if isinstance(f_emis_dt, datetime):
                     aging_days = (today - f_emis_dt).days
                elif hasattr(f_emis_dt, 'year'): # date object
                     aging_days = (today.date() - f_emis_dt).days
            
            if aging_days < days:
                continue

            item = {
                "Numero": str(d.get('odp_num', '')).strip(),
                "Fecha": f_emis_dt.strftime('%Y-%m-%d') if f_emis_dt else "-",
                "Cierre": str(d.get('cie_num', '')).strip(),
                "DiasVencidos": aging_days
            }
            data.append(item)
            
        return data
    except Exception as e:
        print(f"Error /api/traslados/ordenes-cierre-pendientes: {e}")
        return []
