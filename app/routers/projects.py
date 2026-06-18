from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models import (
    User, Project, ProjectBoard, ProjectList, ProjectCard,
    ProjectComment, ProjectCardMember, ProjectLabel, ProjectCardLabel,
    ProjectChecklist, ProjectChecklistItem,
    ProjectCardStatusHistory, ProjectActivityLog
)
from app.dependencies import get_current_user
from datetime import datetime, timezone, timedelta

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# ─────────────────────────────────────────────────────────────
# Status values that count as "done" for progress calculation
DONE_STATUS_VALUES = {"finalizado"}

def _project_progress(project: Project):
    """Calcula progreso global y por fase del proyecto."""
    total = done = 0
    phases = []
    for board in project.boards:
        b_total = b_done = 0
        for lst in board.lists:
            for card in lst.cards:
                b_total += 1
                if (card.status or "").strip().lower() in DONE_STATUS_VALUES:
                    b_done += 1
        total  += b_total
        done   += b_done
        pct_b   = round((b_done / b_total * 100) if b_total else 0, 1)
        phases.append({
            "id": board.id,
            "title": board.title,
            "total": b_total,
            "done": b_done,
            "pct": pct_b,
        })
    pct_global = round((done / total * 100) if total else 0, 1)
    return {"total": total, "done": done, "pct": pct_global, "phases": phases}

# ─────────────────────────────────────────────────────────────
# HTML VIEWS
# ─────────────────────────────────────────────────────────────

@router.get("/projects", response_class=HTMLResponse)
def get_projects_list(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login")
    if user.role not in [1, 2, 3, 4, 8]:
        return RedirectResponse(url="/dashboard")

    projects = db.query(Project).order_by(Project.created_at).all()

    # Calcular progreso para cada proyecto
    projects_data = []
    for p in projects:
        prog = _project_progress(p)
        projects_data.append({
            "id": p.id,
            "name": p.name,
            "description": p.description or "",
            "background": p.background,
            "board_count": len(p.boards),
            "pct": prog["pct"],
            "total_cards": prog["total"],
            "done_cards": prog["done"],
            "created_at": p.created_at,
        })

    return templates.TemplateResponse("projects/index.html", {
        "request": request,
        "user": user,
        "title": "Mis Proyectos",
        "projects": projects_data,
    })


@router.get("/projects/{project_id}", response_class=HTMLResponse)
def get_project_detail(request: Request, project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login")

    # ── Intentar como Project primero ────────────────────────
    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        progress = _project_progress(project)
        return templates.TemplateResponse("projects/detail.html", {
            "request": request,
            "user": user,
            "title": project.name,
            "project": project,
            "progress": progress,
        })

    # ── Compatibilidad backward: puede ser un board_id antiguo ──
    board = db.query(ProjectBoard).filter(ProjectBoard.id == project_id).first()
    if board:
        # Servir el tablero directamente (el URL viejo /projects/{board_id} sigue funcionando)
        return templates.TemplateResponse("projects/board.html", {
            "request": request,
            "user": user,
            "title": board.title,
            "board": board,
            "project_id": board.project_id or "",
            "now_date": datetime.now(timezone.utc)
        })

    raise HTTPException(status_code=404, detail="Proyecto no encontrado")


@router.get("/projects/{project_id}/boards/{board_id}", response_class=HTMLResponse)
def get_project_board(request: Request, project_id: str, board_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    board = db.query(ProjectBoard).filter(
        ProjectBoard.id == board_id,
        ProjectBoard.project_id == project_id
    ).first()
    if not board:
        raise HTTPException(status_code=404, detail="Tablero no encontrado")

    return templates.TemplateResponse("projects/board.html", {
        "request": request,
        "user": user,
        "title": board.title,
        "board": board,
        "project_id": project_id,
        "now_date": datetime.now(timezone.utc)
    })


# ─────────────────────────────────────────────────────────────
# API — PROJECTS CRUD
# ─────────────────────────────────────────────────────────────

@router.get("/api/projects")
def api_list_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    projects = db.query(Project).order_by(Project.created_at).all()
    result = []
    for p in projects:
        prog = _project_progress(p)
        result.append({
            "id": p.id, "name": p.name, "description": p.description,
            "background": p.background, "board_count": len(p.boards),
            "pct": prog["pct"], "total_cards": prog["total"],
        })
    return result


@router.post("/api/projects")
def api_create_project(
    name: str = Form(...),
    description: str = Form(""),
    background: str = Form("#1e1b4b"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if not user:
        raise HTTPException(status_code=401)

    project = Project(name=name, description=description, background=background)
    db.add(project)
    db.flush()  # get project.id before commit

    # Etiquetas predefinidas del nuevo proyecto
    DEFAULT_LABELS = [
        ("Urgente",    "#ef4444"),
        ("En Proceso", "#f59e0b"),
        ("Detenido",   "#6b7280"),
    ]
    for lbl_name, lbl_color in DEFAULT_LABELS:
        db.add(ProjectLabel(name=lbl_name, color=lbl_color, project_id=project.id))

    db.commit()
    db.refresh(project)
    return {"message": "Proyecto creado", "id": project.id}


@router.delete("/api/projects/{project_id}")
def api_delete_project(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not user or user.role not in [1, 2, 4]:
        raise HTTPException(status_code=403)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404)

    # Todos deben eliminar en orden jerárquico
    for board in project.boards:
        for lst in board.lists:
            card_count = len(lst.cards)
            if card_count > 0:
                raise HTTPException(
                    status_code=422,
                    detail=f"La fase '{board.title}' contiene la lista '{lst.title}' con {card_count} tarjeta(s). Elimina las tarjetas primero."
                )
        list_count = len(board.lists)
        if list_count > 0:
            raise HTTPException(
                status_code=422,
                detail=f"La fase '{board.title}' tiene {list_count} lista(s). Elimínalas desde el tablero Kanban."
            )
    board_count = len(project.boards)
    if board_count > 0:
        raise HTTPException(
            status_code=422,
            detail=f"El proyecto tiene {board_count} fase(s). Elimínalas primero."
        )
    db.delete(project)
    db.commit()
    return {"message": "Proyecto eliminado"}


@router.get("/api/projects/{project_id}/progress")
def api_project_progress(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404)
    return _project_progress(project)


@router.get("/api/projects/{project_id}/labels")
def api_project_labels(project_id: str, db: Session = Depends(get_db)):
    labels = db.query(ProjectLabel).filter(ProjectLabel.project_id == project_id).all()
    return [{"id": l.id, "name": l.name, "color": l.color} for l in labels]


@router.post("/api/projects/{project_id}/labels")
def api_create_project_label(
    project_id: str,
    name: str = Form(...),
    color: str = Form("#3b82f6"),
    db: Session = Depends(get_db)
):
    lbl = ProjectLabel(name=name, color=color, project_id=project_id)
    db.add(lbl)
    db.commit()
    db.refresh(lbl)
    return {"message": "Etiqueta creada", "id": lbl.id}


# ─────────────────────────────────────────────────────────────
# API — BOARDS (ahora dentro de un Project)
# ─────────────────────────────────────────────────────────────

@router.post("/api/projects/{project_id}/boards")
def api_create_board_in_project(
    project_id: str,
    title: str = Form(...),
    background: str = Form("#714B67"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    board = ProjectBoard(title=title, background=background, project_id=project_id)
    db.add(board)
    db.commit()
    db.refresh(board)
    return {"message": "Fase creada", "id": board.id}


@router.delete("/api/projects/{project_id}/boards/{board_id}")
def api_delete_board_in_project(
    project_id: str,
    board_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    board = db.query(ProjectBoard).filter(
        ProjectBoard.id == board_id,
        ProjectBoard.project_id == project_id
    ).first()
    if not board:
        raise HTTPException(status_code=404)

    # Todos deben eliminar en orden jerárquico
    for lst in board.lists:
        card_count = len(lst.cards)
        if card_count > 0:
            raise HTTPException(
                status_code=422,
                detail=f"La lista '{lst.title}' tiene {card_count} tarjeta(s). Elimina las tarjetas primero."
            )
    list_count = len(board.lists)
    if list_count > 0:
        raise HTTPException(
            status_code=422,
            detail=f"La fase '{board.title}' tiene {list_count} lista(s). Elimínalas primero desde el tablero Kanban."
        )
    db.delete(board)
    db.commit()
    return {"message": "Fase eliminada"}


# ─── Compatibilidad legado: mantener la ruta vieja /api/projects/boards ──────

@router.post("/api/projects/boards")
def create_board(title: str = Form(...), background: str = Form("#714B67"), db: Session = Depends(get_db)):
    board = ProjectBoard(title=title, background=background)
    db.add(board)
    db.commit()
    db.refresh(board)
    return {"message": "Tablero creado", "id": board.id}

@router.delete("/api/projects/boards/{board_id}")
def delete_board(board_id: str, db: Session = Depends(get_db)):
    board = db.query(ProjectBoard).filter(ProjectBoard.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404)
    db.delete(board)
    db.commit()
    return {"message": "Tablero eliminado"}


@router.post("/api/projects/boards/{board_id}/lists")
def create_list(board_id: str, title: str = Form(...), db: Session = Depends(get_db)):
    # Calculate last order
    last_list = db.query(ProjectList).filter(ProjectList.board_id == board_id).order_by(ProjectList.order.desc()).first()
    new_order = (last_list.order + 1000.0) if last_list else 1000.0
    
    plist = ProjectList(title=title, order=new_order, board_id=board_id)
    db.add(plist)
    db.commit()
    db.refresh(plist)
    return {"message": "Lista creada", "id": plist.id, "order": plist.order}

@router.delete("/api/projects/lists/{list_id}")
def delete_list(list_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plist = db.query(ProjectList).filter(ProjectList.id == list_id).first()
    if not plist:
        raise HTTPException(status_code=404)

    # Todos deben eliminar tarjetas primero
    card_count = len(plist.cards)
    if card_count > 0:
        raise HTTPException(
            status_code=422,
            detail=f"La lista '{plist.title}' tiene {card_count} tarjeta(s). Elimina las tarjetas primero."
        )
    db.delete(plist)
    db.commit()
    return {"message": "Lista eliminada"}

@router.post("/api/projects/lists/{list_id}/cards")
def create_card(list_id: str, title: str = Form(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Calculate last order
    last_card = db.query(ProjectCard).filter(ProjectCard.list_id == list_id).order_by(ProjectCard.order.desc()).first()
    new_order = (last_card.order + 1000.0) if last_card else 1000.0
    
    card = ProjectCard(title=title, order=new_order, list_id=list_id)
    db.add(card)
    db.commit()
    db.refresh(card)
    
    # Audit Log
    log = ProjectActivityLog(card_id=card.id, user_id=user.id if user else None, action_type="created", description="Tarjeta creada")
    db.add(log)
    db.commit()
    
    return {"message": "Tarjeta creada", "id": card.id, "order": card.order}

# DRAG AND DROP: Update card position natively!
@router.post("/api/projects/cards/{card_id}/move")
def move_card(
    card_id: str, 
    new_list_id: str = Form(...), 
    prev_order: float = Form(0.0), 
    next_order: float = Form(0.0), 
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    card = db.query(ProjectCard).filter(ProjectCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")
        
    old_list_id = card.list_id
    
    if old_list_id != new_list_id:
        db.add(ProjectCardStatusHistory(card_id=card.id, old_list_id=old_list_id, new_list_id=new_list_id, user_id=user.id if user else None))
        db.add(ProjectActivityLog(card_id=card.id, user_id=user.id if user else None, action_type="moved", description="Movida a otra lista"))
        
    card.list_id = new_list_id
    
    # The magical SQL Math for interpolation (No massive updates needed!)
    # Scenarios:
    # 1. Dropped at top: next_order is X, prev_order is 0. New order = X / 2
    # 2. Dropped at bottom: prev_order is Y, next_order is 0. New order = Y + 1000
    # 3. Dropped in between: new order = (prev_order + next_order) / 2
    
    if prev_order == 0.0 and next_order > 0.0:
        new_order = next_order / 2.0
    elif prev_order > 0.0 and next_order == 0.0:
        new_order = prev_order + 1000.0
    elif prev_order > 0.0 and next_order > 0.0:
        new_order = (prev_order + next_order) / 2.0
    else:
        # Prev 0 and Next 0 means it's the only one in the list
        new_order = 1000.0
        
    card.order = new_order
    db.commit()
    return {"message": "Movido OK", "new_order": new_order}

@router.post("/api/projects/lists/{list_id}/move")
def move_list(
    list_id: str, 
    prev_order: float = Form(0.0), 
    next_order: float = Form(0.0), 
    db: Session = Depends(get_db)
):
    plist = db.query(ProjectList).filter(ProjectList.id == list_id).first()
    if not plist:
        raise HTTPException(status_code=404, detail="Lista no encontrada")
        
    if prev_order == 0.0 and next_order > 0.0:
        new_order = next_order / 2.0
    elif prev_order > 0.0 and next_order == 0.0:
        new_order = prev_order + 1000.0
    elif prev_order > 0.0 and next_order > 0.0:
        new_order = (prev_order + next_order) / 2.0
    else:
        new_order = 1000.0
        
    plist.order = new_order
    db.commit()
    return {"message": "Movido OK", "new_order": new_order}

@router.put("/api/projects/cards/{card_id}")
def update_card(
    card_id: str, 
    title: str = Form(None),
    description: str = Form(None), 
    color: str = Form(None), 
    due_date: str = Form(None),
    start_date: str = Form(None),
    parent_id: str = Form(None),
    is_milestone: bool = Form(None),
    story_points: float = Form(None),
    status: str = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    card = db.query(ProjectCard).filter(ProjectCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404)
        
    def add_log(desc, old_val, new_val):
        if old_val != new_val:
            db.add(ProjectActivityLog(card_id=card.id, user_id=user.id if user else None, action_type="updated", description=desc, old_value=str(old_val), new_value=str(new_val)))

    if title is not None and card.title != title:
        add_log("Título modificado", card.title, title)
        card.title = title
        
    if description is not None and card.description != description:
        add_log("Descripción modificada", card.description, description)
        card.description = description
        
    if color is not None:
        card.color = color
        
    if parent_id is not None:
        new_parent = parent_id if parent_id.strip() != "" else None
        if card.parent_id != new_parent:
            add_log("Dependencia Padre modificada", card.parent_id, new_parent)
            card.parent_id = new_parent
            
    if is_milestone is not None:
        card.is_milestone = is_milestone
        
    if story_points is not None:
        card.story_points = story_points

    if status is not None and status.strip() in {"Por Hacer", "En Proceso", "Finalizado"}:
        if card.status != status.strip():
            add_log("Estado cambiado", card.status, status.strip())
            card.status = status.strip()

    if start_date is not None:
        if start_date.strip() == "":
            card.start_date = None
        else:
            try:
                card.start_date = datetime.strptime(start_date, "%Y-%m-%d")
            except:
                pass

    if due_date is not None:
        old_date = card.due_date
        if due_date.strip() == "":
            card.due_date = None
        else:
            try:
                card.due_date = datetime.strptime(due_date, "%Y-%m-%d")
            except:
                pass
                
        # Cascade Date Sync Logic!
        if old_date and card.due_date and old_date.date() != card.due_date.date():
            delta_days = (card.due_date.date() - old_date.date()).days
            
            # Find direct children
            children = db.query(ProjectCard).filter(ProjectCard.parent_id == card.id).all()
            for child in children:
                if child.due_date:
                    old_cdd = child.due_date
                    child.due_date = child.due_date + timedelta(days=delta_days)
                    db.add(ProjectActivityLog(card_id=child.id, user_id=user.id if user else None, action_type="cascade", description="Cascada: Desplazamiento por Padre", old_value=str(old_cdd.date()), new_value=str(child.due_date.date())))
                if child.start_date:
                    child.start_date = child.start_date + timedelta(days=delta_days)

    db.commit()
    return {"message": "Ok"}

@router.delete("/api/projects/cards/{card_id}")
def delete_card(card_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    card = db.query(ProjectCard).filter(ProjectCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404)
    db.delete(card)
    db.commit()
    # Activity logs are CASCADE deleted by the DB, no need to log deleted cards
    return {"message": "Eliminado"}

# --- Modal Card Data ---

@router.get("/api/projects/cards/{card_id}")
def get_card_details(card_id: str, db: Session = Depends(get_db)):
    card = db.query(ProjectCard).filter(ProjectCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404)
    
    return {
        "id": card.id,
        "title": card.title,
        "description": card.description or "",
        "due_date": card.due_date.strftime("%Y-%m-%d") if card.due_date else "",
        "status": card.status or "Por Hacer",
        "list_id": card.list_id,
        "members": [{"id": m.user.id, "username": m.user.username} for m in card.members if m.user],
        "checklists": [
            {
                "id": cl.id, 
                "title": cl.title,
                "items": [{"id": it.id, "text": it.text, "is_completed": it.is_completed} for it in cl.items]
            } for cl in card.checklists
        ],
        "labels": [{"id": l.label.id, "name": l.label.name, "color": l.label.color} for l in card.labels if l.label]
    }

# --- Members ---

@router.get("/api/projects/users")
def get_assignable_users(db: Session = Depends(get_db)):
    users = db.query(User).filter(User.is_active == 1).order_by(User.username).all()
    return [{"id": u.id, "username": u.username} for u in users]

@router.post("/api/projects/cards/{card_id}/members")
def add_card_member(card_id: str, user_id: int = Form(...), db: Session = Depends(get_db)):
    exists = db.query(ProjectCardMember).filter_by(card_id=card_id, user_id=user_id).first()
    if not exists:
        m = ProjectCardMember(card_id=card_id, user_id=user_id)
        db.add(m)
        db.commit()
    return {"message": "Miembro asignado"}

@router.delete("/api/projects/cards/{card_id}/members/{user_id}")
def remove_card_member(card_id: str, user_id: int, db: Session = Depends(get_db)):
    m = db.query(ProjectCardMember).filter_by(card_id=card_id, user_id=user_id).first()
    if m:
        db.delete(m)
        db.commit()
    return {"message": "Removido"}

# --- Checklists ---

@router.post("/api/projects/cards/{card_id}/checklists")
def add_checklist(card_id: str, title: str = Form("Checklist"), db: Session = Depends(get_db)):
    cl = ProjectChecklist(card_id=card_id, title=title)
    db.add(cl)
    db.commit()
    return {"message": "Checklist creado"}

@router.post("/api/projects/checklists/{checklist_id}/items")
def add_checklist_item(checklist_id: str, text: str = Form(...), db: Session = Depends(get_db)):
    it = ProjectChecklistItem(checklist_id=checklist_id, text=text)
    db.add(it)
    db.commit()
    return {"message": "Item creado"}

@router.put("/api/projects/checklist_items/{item_id}")
def toggle_checklist_item(item_id: str, is_completed: bool = Form(...), db: Session = Depends(get_db)):
    it = db.query(ProjectChecklistItem).filter_by(id=item_id).first()
    if it:
        it.is_completed = is_completed
        db.commit()
    return {"message": "Actualizado"}

@router.delete("/api/projects/checklist_items/{item_id}")
def delete_checklist_item(item_id: str, db: Session = Depends(get_db)):
    it = db.query(ProjectChecklistItem).filter_by(id=item_id).first()
    if it:
        db.delete(it)
        db.commit()
    return {"message": "Eliminado"}

# --- Labels ---

@router.get("/api/projects/boards/{board_id}/labels")
def get_board_labels(board_id: str, db: Session = Depends(get_db)):
    labels = db.query(ProjectLabel).filter(ProjectLabel.board_id == board_id).all()
    return [{"id": l.id, "name": l.name, "color": l.color} for l in labels]

@router.post("/api/projects/boards/{board_id}/labels")
def create_board_label(board_id: str, name: str = Form(...), color: str = Form("#3b82f6"), db: Session = Depends(get_db)):
    lbl = ProjectLabel(board_id=board_id, name=name, color=color)
    db.add(lbl)
    db.commit()
    db.refresh(lbl)
    return {"message": "Etiqueta creada", "id": lbl.id}

@router.post("/api/projects/cards/{card_id}/labels")
def add_card_label(card_id: str, label_id: str = Form(...), db: Session = Depends(get_db)):
    exists = db.query(ProjectCardLabel).filter_by(card_id=card_id, label_id=label_id).first()
    if not exists:
        cl = ProjectCardLabel(card_id=card_id, label_id=label_id)
        db.add(cl)
        db.commit()
    return {"message": "Etiqueta asignada"}

@router.delete("/api/projects/cards/{card_id}/labels/{label_id}")
def remove_card_label(card_id: str, label_id: str, db: Session = Depends(get_db)):
    cl = db.query(ProjectCardLabel).filter_by(card_id=card_id, label_id=label_id).first()
    if cl:
        db.delete(cl)
        db.commit()
    return {"message": "Removido"}


# --- ANALYTICS AND TRAZA ---

@router.get("/api/projects/cards/{card_id}/metrics")
def get_card_metrics(card_id: str, db: Session = Depends(get_db)):
    card = db.query(ProjectCard).filter(ProjectCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404)
        
    # Checklist %
    total_items = sum(len(cl.items) for cl in card.checklists)
    completed_items = sum(1 for cl in card.checklists for item in cl.items if item.is_completed)
    checklist_progress = (completed_items / total_items * 100) if total_items > 0 else 0.0
    
    # Time in List Calculation
    # We find the latest move to this current list
    last_move = db.query(ProjectCardStatusHistory).filter(
        ProjectCardStatusHistory.card_id == card_id, 
        ProjectCardStatusHistory.new_list_id == card.list_id
    ).order_by(ProjectCardStatusHistory.timestamp.desc()).first()
    
    if last_move:
        delta = datetime.now(timezone.utc).replace(tzinfo=None) - last_move.timestamp.replace(tzinfo=None)
        days_in_list = delta.days
    else:
        # If never moved, time in list is since creation
        delta = datetime.now(timezone.utc).replace(tzinfo=None) - card.created_at.replace(tzinfo=None)
        days_in_list = delta.days
        
    # Get Audit Logs (Timeline)
    logs = db.query(ProjectActivityLog).filter(ProjectActivityLog.card_id == card_id).order_by(ProjectActivityLog.timestamp.desc()).all()
    
    return {
        "checklist_progress_pct": round(checklist_progress, 1),
        "days_in_current_list": days_in_list,
        "logs": [
            {
                "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M"),
                "action": log.action_type,
                "description": log.description,
                "user": log.user.username if log.user else "Sistema"
            } for log in logs
        ]
    }

@router.get("/api/projects/boards/{board_id}/workload")
def get_board_workload(board_id: str, db: Session = Depends(get_db)):
    # Calculate total story points or cards per assigned user in this board
    board = db.query(ProjectBoard).filter(ProjectBoard.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404)
        
    workload = {}
    for lst in board.lists:
        for crd in lst.cards:
            pts = crd.story_points or 1.0 # 1 point per card if not specified
            for mem in crd.members:
                username = mem.user.username
                if username not in workload:
                    workload[username] = {"points": 0, "cards": 0}
                workload[username]["points"] += pts
                workload[username]["cards"] += 1
                
    return workload
