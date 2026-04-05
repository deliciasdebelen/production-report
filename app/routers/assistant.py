from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from .. import models, auth_utils
from ..database import get_db
from ..dependencies import get_current_active_user
from ..ai_knowledge import get_knowledge_response
from ..services.recommendations import get_ai_recommendations
from ..services.analysis_service import analysis_service
from ..external_db import engine_a, engine_m
from sqlalchemy import text
import datetime
from typing import List, Dict

router = APIRouter(
    prefix="/api/assistant",
    tags=["assistant"],
    responses={404: {"description": "Not found"}},
)

# Simple In-Memory History (Per User Session - Simplified)
# In prod, use Redis or DB with SessionID
HISTORY: Dict[str, List[Dict[str, str]]] = {}

@router.post("/chat")
async def assistant_chat(
    message: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    user_id = str(current_user.id)
    if user_id not in HISTORY: HISTORY[user_id] = []
    
    # Context Management
    history = HISTORY[user_id]
    history.append({"role": "user", "content": message})
    if len(history) > 10: history.pop(0) # Keep last 10
    
    msg = message.lower().strip()
    response_text = ""

    try:
        # --- INTENT CLASSIFICATION ---
        
        # 1. SALES ANALYSIS
        if any(x in msg for x in ["ventas", "factura", "cobro", "pedido"]):
            if "hoy" in msg:
                 data = analysis_service.get_sales_summary(datetime.date.today().strftime("%Y-%m-%d"))
                 if data:
                     response_text = (
                         f"**Resumen de Ventas (Hoy)**\n"
                         f"- **Facturas**: {data['num_facturas']}\n"
                         f"- **Total Neto**: {data['total_ventas']:,.2f}\n"
                         f"- **Saldo Pendiente**: {data['saldo_pendiente']:,.2f}"
                     )
                 else:
                     response_text = "No hay registros de ventas para hoy."

        # 2. INVENTORY CHECK
        elif any(x in msg for x in ["stock", "inventario", "existencia"]):
             # Extract article code if possible (simple heuristic)
             words = msg.split()
             target = words[-1] if len(words) > 2 else None
             if target:
                 stock = analysis_service.get_stock_check(target)
                 if stock:
                     item_lines = [f"- **{s['co_alma']}**: {s['stock_act']:,.2f} ({s['art_des']})" for s in stock]
                     response_text = f"**Stock para '{target}':**\n" + "\n".join(item_lines)
                 else:
                     response_text = f"No encontré stock para el artículo que parece ser '{target}'."
             else:
                 response_text = "Para consultar inventario, por favor especifica el código o nombre. Ejemplo: 'Stock de MP01'."

        # 3. DIAGNOSTICS (AUDIT)
        elif "error" in msg or "lote" in msg:
             # Extract GUID if present (regex would be better, simplistic for now)
             import re
             guid_match = re.search(r'[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}', message, re.I)
             if guid_match:
                 guid = guid_match.group(0)
                 diag = analysis_service.diagnose_batch_error(guid)
                 if diag['status'] == 'DETECTED':
                     response_text = (
                         f"**Diagnóstico de Error de Lote**\n"
                         f"- **GUID**: `{guid}`\n"
                         f"- **Problema**: {diag['type']}\n"
                         f"- **Detalle**: {diag['details']}\n"
                         f"- **Recomendación**: {diag['recommendation']}"
                     )
                 else:
                     response_text = f"Analicé el GUID `{guid}` pero no encontré registros específicos de error en las tablas de lotes."
             else:
                 # Fallback to general diagnostic if no GUID
                 statuses = []
                 try:
                    analysis_service._execute_a("SELECT 1")
                    statuses.append("✅ **carmal_a**: Conectado")
                 except: statuses.append("❌ **carmal_a**: Error")
                 
                 kb_response = get_knowledge_response(msg)
                 response_text = f"Diagnóstico General:\n" + "\n".join(statuses)
                 if kb_response: response_text += f"\n\n{kb_response}"

        # 5. DISPATCH AUDIT INTENT (via chat)
        elif any(x in msg for x in ["auditar despacho", "revisar facturas", "duplicado", "factura duplicada", "verificar guia", "buscar duplicado"]):
            response_text = (
                "Para auditar facturas o notas de entrega contra el histórico de guías, "
                "usa el endpoint **POST /api/assistant/audit-dispatch** con el campo "
                "`doc_numbers` (lista separada por comas). Ejemplo:\n"
                "```\nPOST /api/assistant/audit-dispatch\ndoc_numbers=000001,000002,NE-003\n```\n"
                "El sistema te indicará si algún documento ya vive en una guía existente."
            )

        # 4. KNOWLEDGE BASE (Fallback)
        if not response_text:
            kb = get_knowledge_response(msg)
            if kb: response_text = kb
            else: 
                # Use history context to handle "gracias" or follow-ups roughly
                if "gracias" in msg:
                    response_text = "De nada. ¿Necesitas ayuda con algo más?"
                else:
                    response_text = "Entendido. ¿Necesitas analizar ventas, inventario, auditar facturas de despacho o revisar algún error técnico?"

        # Save History
        history.append({"role": "assistant", "content": response_text})
        return {"response": response_text}

    except Exception as e:
        print(f"Chat Error: {e}")
        return {"response": "Ocurrió un error interno al procesar tu solicitud."}


# ─────────────────────────────────────────────────────────────────────────────
# AUDITOR DE INTEGRIDAD DE DESPACHOS
# Endpoint preventivo: recibe lista de facturas/notas y detecta duplicados
# contra el histórico de Guías de Despacho ya registradas.
# ─────────────────────────────────────────────────────────────────────────────

from ..models import LogisticsDispatch
import json as _json

@router.post("/audit-dispatch")
async def audit_dispatch_documents(
    doc_numbers: str = Form(..., description="Números de factura o nota de entrega, separados por coma"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Auditor Preventivo de Despachos.

    Recibe una lista de números de documento (facturas / notas de entrega)
    y los compara contra TODOS los renglones de guías de despacho activas
    (is_annulled = False).

    Retorna:
    - duplicates: lista con los conflictos encontrados
    - clean:      lista de documentos sin conflicto
    - summary:    texto legible para mostrar en el chat/asistente
    """
    # Normalizar lista de documentos
    raw_docs = [d.strip() for d in doc_numbers.split(",") if d.strip()]
    if not raw_docs:
        raise HTTPException(status_code=400, detail="Debe proporcionar al menos un número de documento.")

    # Cargar todas las guías activas (no anuladas) de una sola consulta
    active_dispatches = (
        db.query(LogisticsDispatch)
        .filter(LogisticsDispatch.is_annulled == False)
        .all()
    )

    # Construir índice: doc_num → [(guide_ref, client, date), ...]
    doc_index: dict = {}
    for dispatch in active_dispatches:
        try:
            items_list = _json.loads(dispatch.items_json or "[]")
        except Exception:
            items_list = []

        for item in items_list:
            fact_val = str(item.get("fact", "")).strip()
            if not fact_val:
                continue
            # Normalizar: quitar prefijos tipo "FACT:", "NOTA:" etc.
            clean_fact = fact_val.split(":")[-1].strip()

            if clean_fact not in doc_index:
                doc_index[clean_fact] = []

            doc_index[clean_fact].append({
                "guide_ref":  dispatch.document_ref,
                "client":     dispatch.client_destination,
                "date":       dispatch.date.strftime("%d/%m/%Y") if dispatch.date else "—",
                "dispatch_id": dispatch.id,
                "article":    str(item.get("item", "")).strip(),
                "qty":        item.get("qty", 0),
            })

    # Clasificar cada documento solicitado
    duplicates = []
    clean      = []

    for doc in raw_docs:
        # Buscar con y sin prefijo
        hits = doc_index.get(doc) or doc_index.get(doc.split(":")[-1].strip(), [])
        if hits:
            duplicates.append({
                "doc_number": doc,
                "conflicts":  hits
            })
        else:
            clean.append(doc)

    # Construir resumen legible
    if not duplicates:
        summary = (
            f"Todos los {len(clean)} documento(s) auditados son nuevos. "
            "No se detectaron duplicados en el histórico de guías."
        )
    else:
        lines = [f"Se detectaron **{len(duplicates)} documento(s) duplicado(s)**:\n"]
        for dup in duplicates:
            lines.append(f"\n**Factura/Nota: {dup['doc_number']}** — ya registrada en:")
            for c in dup["conflicts"]:
                lines.append(
                    f"  · Guía **{c['guide_ref']}** | "
                    f"Cliente: {c['client']} | "
                    f"Fecha: {c['date']} | "
                    f"Artículo: {c['article']} ({c['qty']})"
                )
        if clean:
            lines.append(f"\nDocumento(s) sin conflicto: {', '.join(clean)}")
        summary = "\n".join(lines)

    return {
        "audited":    raw_docs,
        "duplicates": duplicates,
        "clean":      clean,
        "total_audited":    len(raw_docs),
        "total_duplicates": len(duplicates),
        "summary":    summary
    }
