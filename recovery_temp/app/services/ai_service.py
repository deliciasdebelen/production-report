
import os
import json
from sqlalchemy.orm import Session
from .. import models
from ..ai_knowledge import get_knowledge_response, PROFIT_PLUS_KNOWLEDGE, SYSTEM_INFO
from ..services.recommendations import get_ai_recommendations
from ..services.stock_solver import StockSolver
from ..routers.assistant import get_dashboard_stats
from ..external_db import engine_a, engine_m
from sqlalchemy import text
# To avoid circular imports, we might need to duplicate the dashboard logic or move it to a service. 
# For now, let's assume we can fetch data directly via DB queries similar to dashboard.

class AIService:
    def __init__(self, db: Session, user: models.User):
        self.db = db
        self.user = user
        # Placeholder for API Client (OpenAI/Anthropic)
        self.api_key = os.getenv("AI_API_KEY") 
        self.provider = os.getenv("AI_PROVIDER", "mock") # mock, openai, anthropic, ollama

    def process_message(self, message: str) -> str:
        """
        Process the user message using RAG and LLM (or fallback logic).
        """
        msg_lower = message.lower().strip()
        
        # 0. System Status (Immediate handling to preserve legacy behavior)
        if any(x in msg_lower for x in ["estatus", "status", "conexion", "salud"]):
            return self._check_system_health()

        # 1. Intent Classification (Simple Rule-based for now, effectively "Pre-computation")
        context = ""
        
        # A. Dashboard / Stats Context
        if any(x in msg_lower for x in ["produccion", "resumen", "hoy", "ayer", "dashboard"]):
            stats = self._get_dashboard_summary()
            context += f"\n[SYSTEM DATA - DASHBOARD]:\n{json.dumps(stats, indent=2)}\n"

        # B. Stock / Solver Context
        if any(x in msg_lower for x in ["stock", "inventario", "error", "problema", "mermas"]):
            diagnostics = StockSolver.get_diagnostics()
             # Summarize diagnostics to save tokens
            diag_summary = [f"{d['type']}: {d['title']}" for d in diagnostics]
            context += f"\n[SYSTEM DATA - DIAGNOSTICS]:\nFound {len(diagnostics)} issues: {', '.join(diag_summary)}\n"

        # C. Knowledge Base Context
        # We can inject relevant parts of PROFIT_PLUS_KNOWLEDGE
        if "inventario" in msg_lower:
             context += f"\n[KNOWLEDGE - INVENTARIO]:\n{PROFIT_PLUS_KNOWLEDGE['inventario']}\n"
        if "manufactura" in msg_lower:
             context += f"\n[KNOWLEDGE - MANUFACTURA]:\n{PROFIT_PLUS_KNOWLEDGE['manufactura']}\n"

        # 2. Generate Response
        if self.provider == "mock":
             return self._mock_response(message, context)
        else:
             return self._llm_response(message, context)

    def _get_dashboard_summary(self):
        # Re-implementing a lightweight version of dashboard stats or importing
        # For simplicity, let's call the logic from models or a utility if possible.
        # Since it's in main.py (not ideal), we'll do a quick query here.
        import datetime
        today = datetime.date.today()
        start = datetime.datetime.combine(today, datetime.time.min)
        
        reports = self.db.query(models.ProductionReport).filter(models.ProductionReport.created_at >= start).all()
        total_kg = sum((r.kg_produced or 0) for r in reports)
        total_units = sum((r.pt_units or 0) for r in reports)
        
        return {
            "date": str(today),
            "total_kg": total_kg,
            "total_units": total_units,
            "batches": len(reports)
        }

    def _mock_response(self, message: str, context: str) -> str:
        """
        Fallback when no AI provider is configured.
        Simulates an intelligent response using the context.
        """
        # Try existing rule-based fallback
        kb_resp = get_knowledge_response(message)
        if kb_resp: return kb_resp
        
        # Dynamic Mocking based on context availability
        response = f"He analizado tu solicitud: '{message}'.\n\n"
        
        if "[SYSTEM DATA - DASHBOARD]" in context:
            data = json.loads(context.split("[SYSTEM DATA - DASHBOARD]:\n")[1].split("\n[")[0])
            response += f"📊 **Resumen de Hoy**: Llevamos producidos **{data['total_kg']:.2f} Kg** en {data['batches']} lotes.\n"
            
        if "[SYSTEM DATA - DIAGNOSTICS]" in context:
             issues_line = context.split("[SYSTEM DATA - DIAGNOSTICS]:\n")[1].strip()
             response += f"⚠️ **Diagnóstico**: {issues_line}\n"
             if "Found 0 issues" not in issues_line:
                 response += "Te recomiendo revisar la pestaña de 'Alertas' o 'Visor' para más detalles."

        if not "[SYSTEM DATA" in context and not kb_resp:
             response += "No tengo información específica sobre eso en mi base de conocimientos actual. Activa un proveedor LLM para conversar libremente."

        return response

    def _check_system_health(self) -> str:
        statuses = []
        try:
            statuses.append("✅ **production.db** (Local): Conectado")
        except:
            statuses.append("❌ **production.db** (Local): Error")

        try:
            with engine_a.connect() as conn:
                    conn.execute(text("SELECT 1"))
            statuses.append("✅ **carmal_a** (Administrativo): Conectado")
        except Exception as e:
            statuses.append(f"❌ **carmal_a**: Error ({str(e)[:20]}...)")

        try:
            with engine_m.connect() as conn:
                    conn.execute(text("SELECT 1"))
            statuses.append("✅ **carmal_m** (Manufactura): Conectado")
        except Exception as e:
            statuses.append(f"❌ **carmal_m**: Error ({str(e)[:20]}...)")
        
        return "Diagnóstico de conexión:<br>" + "<br>".join(statuses)

    def _llm_response(self, message: str, context: str) -> str:
        # TODO: Implement OpenAI / Claude / Ollama call here
        return "LLM Provider not yet implemented."
