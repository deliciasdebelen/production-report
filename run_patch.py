import re

file_path = r"c:\Users\ovargas\Projects\production-report\app\routers\projects.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Imports
content = content.replace(
    "from app.models import User, ProjectBoard, ProjectList, ProjectCard, ProjectComment, ProjectCardMember, ProjectLabel, ProjectCardLabel, ProjectChecklist, ProjectChecklistItem",
    "from app.models import User, ProjectBoard, ProjectList, ProjectCard, ProjectComment, ProjectCardMember, ProjectLabel, ProjectCardLabel, ProjectChecklist, ProjectChecklistItem, ProjectCardStatusHistory, ProjectActivityLog"
)

content = content.replace(
    "from datetime import datetime, timezone",
    "from datetime import datetime, timezone, timedelta"
)

# 2. create_card
create_card_old = """@router.post("/api/projects/lists/{list_id}/cards")
def create_card(list_id: str, title: str = Form(...), db: Session = Depends(get_db)):
    # Calculate last order
    last_card = db.query(ProjectCard).filter(ProjectCard.list_id == list_id).order_by(ProjectCard.order.desc()).first()
    new_order = (last_card.order + 1000.0) if last_card else 1000.0
    
    card = ProjectCard(title=title, order=new_order, list_id=list_id)
    db.add(card)
    db.commit()
    db.refresh(card)
    return {"message": "Tarjeta creada", "id": card.id, "order": card.order}"""

create_card_new = """@router.post("/api/projects/lists/{list_id}/cards")
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
    
    return {"message": "Tarjeta creada", "id": card.id, "order": card.order}"""

content = content.replace(create_card_old, create_card_new)

# 3. move_card
move_card_old = """@router.post("/api/projects/cards/{card_id}/move")
def move_card(
    card_id: str, 
    new_list_id: str = Form(...), 
    prev_order: float = Form(0.0), 
    next_order: float = Form(0.0), 
    db: Session = Depends(get_db)
):
    card = db.query(ProjectCard).filter(ProjectCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")
        
    card.list_id = new_list_id"""

move_card_new = """@router.post("/api/projects/cards/{card_id}/move")
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
        
    card.list_id = new_list_id"""

content = content.replace(move_card_old, move_card_new)

# 4. update_card
update_card_old = """@router.put("/api/projects/cards/{card_id}")
def update_card(
    card_id: str, 
    title: str = Form(None),
    description: str = Form(None), 
    color: str = Form(None), 
    due_date: str = Form(None),
    db: Session = Depends(get_db)
):
    card = db.query(ProjectCard).filter(ProjectCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404)
    if title is not None:
        card.title = title
    if description is not None:
        card.description = description
    if color is not None:
        card.color = color
    if due_date is not None:
        if due_date.strip() == "":
            card.due_date = None
        else:
            try:
                # Expecting YYYY-MM-DD
                card.due_date = datetime.strptime(due_date, "%Y-%m-%d")
            except:
                pass
    db.commit()
    return {"message": "Ok"}"""

update_card_new = """@router.put("/api/projects/cards/{card_id}")
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
    return {"message": "Ok"}"""

content = content.replace(update_card_old, update_card_new)


# 5. Delete Card
del_old = """@router.delete("/api/projects/cards/{card_id}")
def delete_card(card_id: str, db: Session = Depends(get_db)):
    card = db.query(ProjectCard).filter(ProjectCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404)
    db.delete(card)
    db.commit()
    return {"message": "Eliminado"}"""

del_new = """@router.delete("/api/projects/cards/{card_id}")
def delete_card(card_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    card = db.query(ProjectCard).filter(ProjectCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404)
    db.delete(card)
    db.commit()
    # Activity logs are CASCADE deleted by the DB, no need to log deleted cards
    return {"message": "Eliminado"}"""

content = content.replace(del_old, del_new)

# 6. Add metrics and workload endpoints at the bottom
new_endpoints = """

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
"""

if "get_board_workload" not in content:
    content += new_endpoints


with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Project router patched successfully")
