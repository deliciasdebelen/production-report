
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
        
    # Parse Items
    items = []
    try:
        items = json.loads(dispatch.items_json)
    except: pass
    
    # Wrap in single group for template compatibility
    groups = [{
        "invoice": (dispatch.document_ref or "Sin Ref"),
        "client_name": dispatch.client_destination,
        "line_items": items,
        "invoice_total": 0.0
    }]
    
    return templates.TemplateResponse("logistics/print_dispatch.html", {
        "request": request,
        "log": dispatch,
        "groups": groups,
        "now": datetime.now()
    })
