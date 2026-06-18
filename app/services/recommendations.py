
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import ProductionReport, AuditLog, ProductionPlanning, AIFunctionality, AIParameter
import datetime

class RecommendationEngine:
    def __init__(self, db: Session):
        self.db = db

    def analyze_and_recommend(self):
        recommendations = []
        
        # 1. WASTE ANALYSIS (Optimization)
        # Check average waste percentage
        # Formula: sum(mp_waste_kg) / sum(kg_produced)
        
        waste_stats = self.db.query(
            func.sum(ProductionReport.mp_waste_kg),
            func.sum(ProductionReport.kg_produced)
        ).filter(ProductionReport.kg_produced > 0).first()
        
        if waste_stats and waste_stats[1] and waste_stats[1] > 0:
            total_waste = waste_stats[0] or 0
            total_prod = waste_stats[1]
            waste_ratio = total_waste / total_prod
            
            if waste_ratio > 0.05: # > 5% Waste
                recommendations.append(
                    f"⚠️ **Optimización**: El desperdicio promedio es del {waste_ratio:.1%}. "
                    f"Se recomienda ajustar el parámetro 'tolerance_threshold' en el módulo Audit o revisar fórmulas en carmal_m."
                )
        
        # 2. AUDIT FREQUENCY (Audit)
        # Check if there are many open audit logs
        open_issues = self.db.query(func.count(AuditLog.id)).filter(AuditLog.status == "Open").scalar()
        if open_issues > 10:
             recommendations.append(
                f"🛡️ **Auditoría**: Hay {open_issues} incidencias abiertas. "
                f"Se recomienda activar el módulo 'Predictive' para detectar anomalías antes de que ocurran."
             )

        # 3. PLANNING DELAYS (Predictive)
        # Check expired planning orders that are still pending
        today = datetime.date.today().strftime("%Y-%m-%d")
        delayed_orders = self.db.query(func.count(ProductionPlanning.id)).filter(
            ProductionPlanning.status == "Pending",
            ProductionPlanning.date < today
        ).scalar()
        
        if delayed_orders > 0:
             recommendations.append(
                f"🛑 **Planificación**: Hay {delayed_orders} órdenes atrasadas. "
                "La IA sugiere priorizar las órdenes con menor 'units_pending'."
             )

        # 4. CONFIGURATION CHECK
        # Check if basic modules are active
        opt_mod = self.db.query(AIFunctionality).filter(AIFunctionality.name == "Optimization").first()
        if opt_mod and not opt_mod.is_active:
             recommendations.append(
                 "💡 **Configuración**: El módulo 'Optimization' está desactivado. Actívelo para permitir el análisis automático de mermas."
             )

        if not recommendations:
            recommendations.append("✅ **Estado Óptimo**: No se detectaron anomalías graves en los datos recientes.")
            
        return recommendations

def get_ai_recommendations(db: Session):
    engine = RecommendationEngine(db)
    return engine.analyze_and_recommend()
