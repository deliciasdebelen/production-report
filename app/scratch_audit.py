with open('/app/app/routers/logistics.py', 'r') as f:
    lines = f.readlines()

# Safety check
if lines[1568].strip().startswith("@router.post") and "annul" in lines[1568]:
    new_code = """@router.post("/api/dispatch/{dispatch_id}/annul")
async def annul_dispatch(
    dispatch_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    external_db: Session = Depends(get_external_db)
):
    if not user: raise HTTPException(401)
    if user.role not in [1, 4]: # Logic or Admin ONLY
        raise HTTPException(status_code=403, detail="No tiene permisos para anular despachos")
        
    dispatch = db.query(LogisticsDispatch).filter(LogisticsDispatch.id == dispatch_id).first()
    if not dispatch:
        raise HTTPException(status_code=404, detail="Guía no encontrada")
        
    if dispatch.is_annulled:
        return {"status": "success", "message": "Esta guía ya estaba anulada."}
        
    # Sincronización con Profit Plus: Limpiar campo5 y campo6
    try:
        external_docs = set()
        
        # 1. Parsear desde document_ref (formato: "GUIA-XXXX | Fact: FACT:XXX,NOTA:YYY")
        if dispatch.document_ref and '| Fact:' in dispatch.document_ref:
            try:
                imported_str = dispatch.document_ref.split('| Fact:')[1].strip()
                for doc in imported_str.split(','):
                    doc = doc.strip()
                    if ':' in doc:
                        parts = doc.split(':', 1)
                        prefix = parts[0].strip().upper()
                        doc_num = parts[1].strip()
                        external_docs.add((prefix, doc_num))
            except Exception as pe:
                print(f"Error parsing document_ref for annulment: {pe}")
                
        # 2. Parsear desde items_json por si acaso
        if dispatch.items_json:
            try:
                import json
                items_list = json.loads(dispatch.items_json)
                for item in items_list:
                    fact = item.get('fact', '').strip()
                    if fact and "Manual" not in fact:
                        if fact.startswith("NOTA:") or fact.startswith("NE:"):
                            doc_num = fact.split(':')[-1].strip()
                            external_docs.add(("NOTA", doc_num))
                        elif fact.startswith("FACT:"):
                            doc_num = fact.split(':')[-1].strip()
                            external_docs.add(("FACT", doc_num))
                        else:
                            external_docs.add(("FACT", fact))
            except Exception as pe:
                print(f"Error parsing items_json for annulment: {pe}")
                
        # 3. Ejecutar las actualizaciones en Profit
        from sqlalchemy import text
        for prefix, doc_num in external_docs:
            table_name = "saFacturaVenta" if prefix == "FACT" else "saNotaEntregaVenta"
            update_sql = f"UPDATE {table_name} SET campo5 = NULL, campo6 = NULL WHERE doc_num LIKE :doc_val"
            external_db.execute(text(update_sql), {"doc_val": f"%{doc_num}%"})
        external_db.commit()
    except Exception as ext_e:
        print(f"Error clearing external DB on annulment: {ext_e}")
        external_db.rollback()
        
    dispatch.is_annulled = True
    db.commit()
    
    return {"status": "success", "message": f"Guía {dispatch.document_ref} anulada exitosamente."}
"""
    lines = lines[:1568] + [new_code + '\n'] + lines[1589:]
    with open('/app/app/routers/logistics.py', 'w') as f:
        f.writelines(lines)
    print("Replacement successful!")
else:
    print("Safety check failed: line at index 1568 is not the expected post annul route decorator!")
