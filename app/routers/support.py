from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app import models, schemas, email_utils
from app.dependencies import get_current_user, get_current_active_user
import uuid
import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File

router = APIRouter(
    prefix="/api/support",
    tags=["support"],
    responses={404: {"description": "Not found"}},
)

# --- CONFIG (Master Data) ---

@router.get("/config", response_model=dict)
def get_support_config(db: Session = Depends(get_db)):
    # Explicit conversion to avoid ORM serialization issues
    departments = [schemas.SupportDepartment.model_validate(x) for x in db.query(models.SupportDepartment).all()]
    status = [schemas.SupportStatus.model_validate(x) for x in db.query(models.SupportStatus).all()]
    priorities = [schemas.SupportPriority.model_validate(x) for x in db.query(models.SupportPriority).order_by(models.SupportPriority.level.asc()).all()]
    types = [schemas.SupportType.model_validate(x) for x in db.query(models.SupportType).all()]
    
    users = db.query(models.User).filter(models.User.is_active == 1).all()
    techs = [{"id": u.id, "username": u.username} for u in users]
    
    settings = db.query(models.SupportSettings).first()
    settings_data = {
        "notification_emails": settings.notification_emails if settings else "",
        "smtp_server": settings.smtp_server if settings else "smtp.gmail.com",
        "smtp_port": settings.smtp_port if settings else 587,
        "smtp_user": settings.smtp_user if settings else "",
        "smtp_password": settings.smtp_password if settings else ""
    }

    return {
        "departments": departments,
        "status": status,
        "priorities": priorities,
        "types": types,
        "technicians": techs,
        "settings": settings_data
    }

@router.post("/settings")
def update_support_settings(
    notification_emails: str = Form(""),
    smtp_server: str = Form("smtp.gmail.com"),
    smtp_port: int = Form(587),
    smtp_user: str = Form(""),
    smtp_password: str = Form(""),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if current_user.role != 4:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    settings = db.query(models.SupportSettings).first()
    if not settings:
        settings = models.SupportSettings(
            notification_emails=notification_emails,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_password=smtp_password
        )
        db.add(settings)
    else:
        settings.notification_emails = notification_emails
        settings.smtp_server = smtp_server
        settings.smtp_port = smtp_port
        settings.smtp_user = smtp_user
        if smtp_password != "********": # Mask to prevent overwriting with fake stars
            settings.smtp_password = smtp_password
        
    db.commit()
    return {"status": "ok"}

@router.get("/email-logs")
def get_email_logs(
    limit: int = 50,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if current_user.role != 4:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    logs = db.query(models.EmailLog).order_by(models.EmailLog.id.desc()).limit(limit).all()
    
    return [
        {
            "id": log.id,
            "recipients": log.recipients,
            "subject": log.subject,
            "status": log.status,
            "error_message": log.error_message,
            "created_at": log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else ""
        }
        for log in logs
    ]

@router.post("/config/{table}")
def update_support_config(table: str, name: str = Form(...), id: Optional[int] = Form(None), 
                          color: Optional[str] = Form(None), level: Optional[int] = Form(None),
                          action: str = Form("create"), # create, delete
                          current_user: models.User = Depends(get_current_active_user),
                          db: Session = Depends(get_db)):
    
    if current_user.role != 4:
        raise HTTPException(status_code=403, detail="Not authorized")

    model = None
    if table == 'department': model = models.SupportDepartment
    elif table == 'status': model = models.SupportStatus
    elif table == 'priority': model = models.SupportPriority
    elif table == 'type': model = models.SupportType
    else: raise HTTPException(400, "Invalid table")

    if action == "delete":
        if not id: raise HTTPException(400, "ID required for delete")
        obj = db.query(model).filter(model.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return {"status": "deleted"}

    # Create/Update
    if id:
        obj = db.query(model).filter(model.id == id).first()
        if not obj: raise HTTPException(404, "Not found")
        obj.name = name
        if color and hasattr(obj, 'color_hex'): obj.color_hex = color
        if level and hasattr(obj, 'level'): obj.level = level
    else:
        obj = model(name=name)
        if color and hasattr(obj, 'color_hex'): obj.color_hex = color
        if level and hasattr(obj, 'level'): obj.level = level
        db.add(obj)
    
    db.commit()
    return {"status": "ok"}

# --- TICKETS ---

# --- TICKETS ---

def generate_ticket_code(db: Session):
    # Pattern: SOP-001 (Sequential)
    # Find last ticket code starting with SOP-
    last = db.query(models.SupportTicket).filter(models.SupportTicket.code.like("SOP-%"))\
             .order_by(models.SupportTicket.id.desc()).first()
    
    if last:
        try:
            # Assumes SOP-XXX
            parts = last.code.split("-")
            seq = int(parts[1]) + 1
        except:
            seq = 1
    else:
        seq = 1
        
    return f"SOP-{str(seq).zfill(3)}"

@router.post("/ticket", response_model=schemas.SupportTicket)
async def create_ticket(
    description: str = Form(...),
    department_id: int = Form(...),
    type_id: int = Form(...),
    priority_id: int = Form(...),
    contact_email: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_active_user)
):
    # 1. Generate Code
    code = generate_ticket_code(db)
    
    # 2. Handle File Upload
    attachment_url = None
    if file:
        try:
            # Ensure directory exists
            upload_dir = "app/static/up/support"
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate safe filename
            file_ext = os.path.splitext(file.filename)[1]
            filename = f"{code}_{uuid.uuid4().hex[:8]}{file_ext}"
            file_path = os.path.join(upload_dir, filename)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            attachment_url = f"/static/up/support/{filename}"
        except Exception as e:
            print(f"File upload error: {e}")

    # 3. Set Initial Status (Abierto)
    status_open = db.query(models.SupportStatus).filter(models.SupportStatus.name == "Abierto").first()
    status_id = status_open.id if status_open else 1 

    # 4. Create DB Record
    db_ticket = models.SupportTicket(
        code=code,
        description=description,
        attachment_url=attachment_url,
        contact_email=contact_email if contact_email and "@" in contact_email else None,
        department_id=department_id,
        type_id=type_id,
        priority_id=priority_id,
        status_id=status_id,
        created_by_id=current_user.id
    )
    
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    
    # 5. Email Notification (Async/Background ideal, but sync for now)
    # Collect recipients
    recipients = []
    if db_ticket.contact_email and "@" in db_ticket.contact_email:
        recipients.append(db_ticket.contact_email)

    priority_name = "Normal"
    p = db.query(models.SupportPriority).get(db_ticket.priority_id)
    if p: priority_name = p.name

    subject = f"[SOPORTE] Ticket Creado: {db_ticket.code}"
    body = f"""
    Hola {current_user.username},
    
    Su ticket ha sido registrado exitosamente.
    
    Código: {db_ticket.code}
    Prioridad: {priority_name}
    
    Descripción:
    {db_ticket.description}
    
    Nos pondremos en contacto pronto.
    """
    
    settings = db.query(models.SupportSettings).first()
    if settings and settings.notification_emails:
        global_emails = [e.strip() for e in settings.notification_emails.split(",") if e.strip()]
        recipients.extend(global_emails)
        
    # Deduplicate
    recipients = list(set(recipients))
    
    if recipients:
        email_utils.send_email(subject, body, recipients)
    return schemas.SupportTicket(
        id=db_ticket.id,
        code=db_ticket.code,
        description=db_ticket.description,
        attachment_url=db_ticket.attachment_url,
        contact_email=db_ticket.contact_email,
        department_id=db_ticket.department_id,
        type_id=db_ticket.type_id,
        priority_id=db_ticket.priority_id,
        status_id=db_ticket.status_id,
        created_by_id=db_ticket.created_by_id,
        assigned_to_id=db_ticket.assigned_to_id,
        created_at=db_ticket.created_at,
        created_by_username=current_user.username
    )

@router.get("/tickets")
def list_tickets(status: str = "all", mine: bool = False, q: str = None, tech_id: str = "all",
                 db: Session = Depends(get_db), 
                 current_user: models.User = Depends(get_current_active_user)):
    
    query = db.query(models.SupportTicket)\
        .options(joinedload(models.SupportTicket.department))\
        .options(joinedload(models.SupportTicket.status))\
        .options(joinedload(models.SupportTicket.priority))\
        .options(joinedload(models.SupportTicket.support_type))\
        .options(joinedload(models.SupportTicket.created_by))

    if mine:
        query = query.filter(models.SupportTicket.created_by_id == current_user.id)
    
    if q:
        # Search by code, desc, or user
        search = f"%{q}%"
        query = query.join(models.User, models.SupportTicket.created_by_id == models.User.id)\
                     .filter(
                         (models.SupportTicket.code.like(search)) | 
                         (models.SupportTicket.description.like(search)) |
                         (models.User.username.like(search))
                     )

    if tech_id and tech_id != "all":
        if tech_id == "unassigned":
            query = query.filter(models.SupportTicket.assigned_to_id == None)
        else:
            try:
                t_id = int(tech_id)
                query = query.filter(models.SupportTicket.assigned_to_id == t_id)
            except:
                pass

    if status != "all":
        # Filter by status ID or name?
        # Let's assume passed ID or 'open'/'closed'
        pass 

    tickets = query.order_by(models.SupportTicket.created_at.desc()).limit(100).all()
    
    # Manual Conversion via Pydantic/Dicts
    result = []
    for t in tickets:
        c_user = t.created_by.username if t.created_by else "Unknown"
        
        # Construct Dict matching Schema structure
        item = {
            "id": t.id,
            "code": t.code,
            "description": t.description,
            "attachment_url": t.attachment_url,
            "contact_email": t.contact_email,
            "department_id": t.department_id,
            "type_id": t.type_id,
            "priority_id": t.priority_id,
            "status_id": t.status_id,
            "created_by_id": t.created_by_id,
            "assigned_to_id": t.assigned_to_id,
            "created_at": t.created_at,
            "closed_at": t.closed_at,
            "department": {'id': t.department.id, 'name': t.department.name} if t.department else None,
            "status": {'id': t.status.id, 'name': t.status.name, 'color_hex': t.status.color_hex} if t.status else None,
            "priority": {'id': t.priority.id, 'name': t.priority.name, 'level': t.priority.level} if t.priority else None,
            "support_type": {'id': t.support_type.id, 'name': t.support_type.name} if t.support_type else None,
            "created_by_username": c_user
        }
        result.append(item)

    return result

@router.patch("/ticket/{id}")
def update_ticket(id: int, update: schemas.SupportTicketUpdate, 
                  db: Session = Depends(get_db), 
                  current_user: models.User = Depends(get_current_active_user)):
    
    if current_user.role != 4:
         raise HTTPException(status_code=403, detail="Not authorized")

    ticket = db.query(models.SupportTicket).filter(models.SupportTicket.id == id).first()
    if not ticket: raise HTTPException(404, "Not found")

    changed = False
    
    if update.status_id:
        ticket.status_id = update.status_id
        # Check if closed
        st = db.query(models.SupportStatus).get(update.status_id)
        if st and st.name == "Cerrado":
             ticket.closed_at = datetime.now()
             if update.close_comment:
                 ticket.close_comment = update.close_comment
        changed = True
        
        # Notify
        recipients = []
        if ticket.contact_email and "@" in ticket.contact_email:
            recipients.append(ticket.contact_email)
        
        settings = db.query(models.SupportSettings).first()
        if settings and settings.notification_emails:
            global_emails = [e.strip() for e in settings.notification_emails.split(",") if e.strip()]
            recipients.extend(global_emails)
            
        recipients = list(set(recipients))
        
        if recipients:
             email_utils.send_email(
                 f"[SOPORTE] Estado Actualizado: {ticket.code}",
                 f"El estado de su ticket ha cambiado a: {st.name}",
                 recipients
             )

    if update.assigned_to_id:
        ticket.assigned_to_id = update.assigned_to_id
        changed = True
        
        # Notify User of Assignment
        if ticket.contact_email:
            # Fetch Technician Name
            tech = db.query(models.User).get(update.assigned_to_id)
            tech_name = tech.username if tech else "Un técnico"
            
            email_utils.send_email(
                f"[SOPORTE] Ticket Asignado: {ticket.code}",
                f"""
                Hola,
                
                Su ticket {ticket.code} ha sido asignado al técnico: {tech_name}.
                
                Pronto recibirá actualizaciones sobre su solicitud.
                
                Atentamente,
                Equipo de Soporte
                """,
                [ticket.contact_email]
            )

    if update.priority_id:
        ticket.priority_id = update.priority_id
        changed = True

    if changed:
        db.commit()
        
    return {"status": "ok"}

@router.get("/report-data")
def get_support_report_data(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = db.query(models.SupportTicket)

    if date_from:
        query = query.filter(models.SupportTicket.created_at >= date_from)
    if date_to:
        query = query.filter(models.SupportTicket.created_at <= f"{date_to} 23:59:59")
    if status_id:
        query = query.filter(models.SupportTicket.status_id == status_id)

    # Group by status — apply date filter but NOT status filter to chart distribution
    from sqlalchemy import func
    status_query = db.query(models.SupportTicket)
    if date_from:
        status_query = status_query.filter(models.SupportTicket.created_at >= date_from)
    if date_to:
        status_query = status_query.filter(models.SupportTicket.created_at <= f"{date_to} 23:59:59")
    if status_id:
        status_query = status_query.filter(models.SupportTicket.status_id == status_id)

    status_counts = db.query(
        models.SupportStatus.name,
        models.SupportStatus.color_hex,
        func.count(models.SupportTicket.id)
    ).outerjoin(models.SupportTicket,
        (models.SupportTicket.status_id == models.SupportStatus.id) &
        (models.SupportTicket.created_at >= date_from if date_from else True) &
        (models.SupportTicket.created_at <= f"{date_to} 23:59:59" if date_to else True)
    ).group_by(models.SupportStatus.id).all()

    status_data = [
        {"name": s[0], "color": s[1] or "#808080", "count": s[2]} 
        for s in status_counts
    ]

    # All filtered tickets with full details for the main table
    all_tickets = query.options(
        joinedload(models.SupportTicket.status),
        joinedload(models.SupportTicket.priority),
        joinedload(models.SupportTicket.department),
        joinedload(models.SupportTicket.created_by)
    ).order_by(models.SupportTicket.created_at.desc()).all()

    tickets_data = []
    for t in all_tickets:
        desc = t.description or ""
        tickets_data.append({
            "code":       t.code,
            "subject":    (desc[:80] + "\u2026") if len(desc) > 80 else desc or "\u2014",
            "date":       t.created_at.strftime("%d/%m/%Y") if t.created_at else "\u2014",
            "updated_at": t.closed_at.strftime("%d/%m/%Y") if t.closed_at else "\u2014",
            "requester":  t.created_by.username if t.created_by else "\u2014",
            "status":     t.status.name if t.status else "Desconocido",
            "priority":   t.priority.name if t.priority else "\u2014",
            "department": t.department.name if t.department else "\u2014",
        })

    # Trend: group by week start (Monday label) for the bar chart
    from collections import defaultdict
    from datetime import timedelta
    week_counts = defaultdict(int)
    for t in all_tickets:
        if t.created_at:
            week_start = t.created_at - timedelta(days=t.created_at.weekday())
            label = week_start.strftime("%d/%m")
            week_counts[label] += 1

    sorted_weeks = sorted(week_counts.items(),
                          key=lambda x: datetime.strptime(x[0], "%d/%m").replace(year=2000))
    trend_data = [{"label": k, "count": v} for k, v in sorted_weeks]

    return {
        "status_distribution": status_data,
        "recent_timeline":     tickets_data,
        "total":               len(tickets_data),
        "trend":               trend_data,
    }

