import re

with open("app/routers/logistics.py", "r") as f:
    content = f.read()

# 1. Update validation logic to ignore 'Anulada' status
old_validation = """        already_dispatched = local_db.query(LogisticsDispatch).filter(
            LogisticsDispatch.items_json.like(f'%"fact": "{doc_num}"%')
            | LogisticsDispatch.items_json.like(f'%"fact": "{doc_num.strip()}"%')
        ).first()"""

new_validation = """        already_dispatched = local_db.query(LogisticsDispatch).filter(
            LogisticsDispatch.items_json.like(f'%"fact": "{doc_num}"%')
            | LogisticsDispatch.items_json.like(f'%"fact": "{doc_num.strip()}"%')
        ).filter(LogisticsDispatch.status != 'Anulada').first()"""

content = content.replace(old_validation, new_validation)

# 2. Add Annul endpoint
old_endpoint = """@router.get("/dispatch/{dispatch_id}/print-labels")"""

new_endpoint = """@router.post("/dispatch/{dispatch_id}/annul")
async def annul_dispatch(dispatch_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dispatch = db.query(LogisticsDispatch).filter(LogisticsDispatch.id == dispatch_id).first()
    if not dispatch:
        raise HTTPException(status_code=404, detail="Guía no encontrada")
    if dispatch.status == 'Anulada':
        raise HTTPException(status_code=400, detail="La guía ya está anulada")
    
    dispatch.status = 'Anulada'
    db.commit()
    return {"message": "Guía anulada correctamente"}

@router.get("/dispatch/{dispatch_id}/print-labels")"""

content = content.replace(old_endpoint, new_endpoint)

with open("app/routers/logistics.py", "w") as f:
    f.write(content)

print("Patched app/routers/logistics.py successfully.")
