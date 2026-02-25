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

        # 4. KNOWLEDGE BASE (Fallback)
        if not response_text:
            kb = get_knowledge_response(msg)
            if kb: response_text = kb
            else: 
                # Use history context to handle "gracias" or follow-ups roughly
                if "gracias" in msg:
                    response_text = "De nada. ¿Necesitas ayuda con algo más?"
                else:
                    response_text = "Entendido. ¿Necesitas analizar ventas, inventario o revisar algún error técnico?"

        # Save History
        history.append({"role": "assistant", "content": response_text})
        return {"response": response_text}

    except Exception as e:
        print(f"Chat Error: {e}")
        return {"response": "Ocurrió un error interno al procesar tu solicitud."}
