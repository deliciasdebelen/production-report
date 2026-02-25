
# AI Knowledge Base & Persona Definition
# "Supervisor Belen" - Industrial Operations Specialist & Profit Plus 2k12 Consultant

SYSTEM_INFO = {
    "server": "192.168.1.79:8000",
    "description": "Production Report System - A bridge between Profit Plus and custom manufacturing logic.",
    "databases": {
        "carmal_a": {
            "name": "carmal_a",
            "engine": "Profit Plus Administrativo 2k12",
            "role": "Comercial, Inventario, Logística",
            "key_tables": ["saFacturaVenta", "saNotaEntregaVenta", "saArticulo", "saCliente", "saProveedor", "saAjuste"]
        },
        "carmal_m": {
            "name": "carmal_m",
            "engine": "Profit Plus Manufactura",
            "role": "Planificación, Fórmulas, Producción",
            "key_tables": ["mpOrdenProduccion", "mpRequisicion", "mpMovimiento"]
        }
    }
}

PROFIT_PLUS_KNOWLEDGE = {
    "inventario": (
        "**Logística e Inventarios (Profit Plus 2k12)**\n"
        "- **Valoración**: El sistema soporta PEPS, UEPS y Promedio Ponderado. Verifique la configuración en *Mantenimiento > Procesos*.\n"
        "- **Ajustes**: Ruta: *Inventario > Procesos > Ajustes de Inventario*. Todo ajuste debe tener un soporte físico auditado.\n"
        "- **Traslados**: Ruta: *Inventario > Procesos > Traslados entre Almacenes*. Garantice que el almacén destino confirme la recepción para mantener la integridad contable."
    ),
    "manufactura": (
        "**Manufactura de Altos Estándares**\n"
        "- **MRP**: La planificación de requerimientos de materiales es vital. Asegure que las fórmulas en *carmal_m* estén actualizadas con las mermas reales.\n"
        "- **Trazabilidad**: Prioridad #1. Todo consumo de Materia Prima debe estar ligado a una Orden de Producción (OP) para asegurar el rastreo por Lote/Serie.\n"
        "- **Calidad**: Implemente puntos de control en la recepción de MP y liberación de PT."
    ),
    "contabilidad": (
        "**Integración Contable**\n"
        "- En Profit Plus, cada movimiento de inventario genera un comprobante contable automático si la interfaz está activa.\n"
        "- Un 'Despacho' sin factura afecta 'Inventario en Tránsito' o 'Costo de Ventas' dependiendo del mapeo de cuentas."
    )
}

class SupervisorPersona:
    def __init__(self):
        self.name = "Supervisor Belén (Powered by Claude-style Logic)"
        self.role = "Especialista Funcional Avanzado en Operaciones Industriales"
        self.tone = "Articulated, precise, helpful, and highly structured (Claude 3.5 Sonnet Persona)."
        self.system_context = "Profit Plus 2k12 Ecosystem (carmal_a, carmal_m, Local DB)"

    def respond(self, query: str) -> str:
        q = query.lower()

        # 1. Identity & Capability (Claude Style)
        if any(x in q for x in ["quien eres", "tu nombre", "modelo", "version"]):
            return (
                f"Soy **{self.name}**, una inteligencia artificial avanzada diseñada para optimizar sus operaciones industriales. "
                "Mi arquitectura está inspirada en los modelos de razonamiento de **Claude**, lo que me permite analizar con precisión "
                "la integridad entre **carmal_a** (Administrativo), **carmal_m** (Manufactura) y su sistema local en **192.168.1.79**.\n\n"
                "Estoy capacitada para ofrecer diagnósticos profundos, recomendaciones de optimización y asistencia técnica en tiempo real."
            )

        # 1.1 Capabilities / Help
        if any(x in q for x in ["que puedes hacer", "que haces", "ayuda", "funciones", "para que sirves", "como mejorarla"]):
            return (
                "**Mis Capacidades Actuales:**\n"
                "1.  **📊 Estatus del Sistema**: Pregunta por 'estatus' o 'conexión' para verificar bases de datos.\n"
                "2.  **🏭 Resumen de Producción**: Pregunta por 'resumen' o 'dashboard' para ver los números de hoy.\n"
                "3.  **🛡️ Diagnóstico de Stock**: Escribe 'problemas de stock' o 'mermas' para buscar errores en inventario.\n"
                "4.  **💡 Expertiz en Profit**: Pregunta sobre 'inventario', 'manufactura' o 'costos' para obtener guías técnicas.\n\n"
                "**¿Cómo mejorarme?**\n"
                "Actualmente opero con reglas estrictas. Para permitirme 'pensar' y responder preguntas abiertas, "
                "necesito ser conectada a un cerebro LLM (como GPT-4). Esto se configura en el `AIService` con una API Key."
            )

        # 2. Database / Technical Architecture
        if any(x in q for x in ["base de datos", "carmal", "db", "arquitectura"]):
            return (
                "El ecosistema operativo se fundamenta en una **Arquitectura de Núcleo Triple**:\n"
                "1.  **carmal_a (SQL Server)**: El centro nervioso administrativo, gestionando inventarios, facturación y logística.\n"
                "2.  **carmal_m (SQL Server)**: El motor de manufactura, controlando formulaciones, órdenes de producción y requerimientos (MRP).\n"
                "3.  **production.db (SQLite Local)**: La capa de inteligencia, auditoría y procesos específicos de su planta.\n\n"
                "Mi función principal es asegurar la **integridad referencial** y la sincronización fluida entre estos tres pilares."
            )

        # 3. Domain Knowledge (Profit Plus - Deep Dive)
        if any(x in q for x in ["inventario", "stock", "almacen"]):
            return (
                "**Gestión Avanzada de Inventarios (Profit Plus 2k12)**\n"
                "Para garantizar la precisión del stock, le sugiero seguir estos protocolos:\n"
                "-   **Valoración**: El sistema admite métodos como PEPS, UEPS y Promedio Ponderado. Verifique su configuración en *Mantenimiento > Procesos*.\n"
                "-   **Ajustes**: Realice ajustes únicamente con soporte físico auditado (*Inventario > Procesos > Ajustes*).\n"
                "-   **Traslados**: Asegure que cada traslado entre almacenes tenga una confirmación de recepción para evitar 'inventarios fantasma'."
            )
        
        if any(x in q for x in ["manufactura", "produccion", "mrp"]):
            return (
                "**Excelencia en Manufactura**\n"
                "La eficiencia productiva depende de la precisión de sus datos:\n"
                "-   **MRP (Material Requirements Planning)**: Mantenga sus fórmulas actualizadas en *carmal_m* para que el cálculo de necesidades sea exacto.\n"
                "-   **Trazabilidad Total**: Es imperativo vincular cada consumo de materia prima a una Orden de Producción (OP). Esto garantiza el rastreo por Lote/Serie.\n"
                "-   **Control de Calidad**: Implemente puntos de validación rigurosos en la recepción de MP y la liberación de PT."
            )

        if any(x in q for x in ["contabilidad", "costo", "financiero"]):
            return (
                "**Integración Contable & Costos**\n"
                "-   En Profit Plus, la automatización es clave: cada movimiento de inventario puede generar un asiento contable inmediato.\n"
                "-   Recuerde: Un 'Despacho' sin factura asociada afectará cuentas transitorias como 'Inventario en Tránsito' o 'Costo de Ventas', dependiendo de su mapeo contable."
            )

        # 4. Process Flow
        if "flujo" in q:
             return (
                 "**Flujo Operativo Estándar (End-to-End)**\n"
                 "He trazado el siguiente recorrido óptimo para sus operaciones:\n"
                 "1.  **Requisición**: Inicie en *Manufactura > Procesos > Requisición*.\n"
                 "2.  **Consumo**: Registre la descarga de MP vinculada estrictamente a la OP.\n"
                 "3.  **Cierre de OP**: Ingrese el Producto Terminado a *carmal_a*.\n"
                 "4.  **Despacho**: Finalice con *Ventas > Procesos > Nota de Entrega/Factura*.\n\n"
                 "*Nota Crítica: La trazabilidad del lote debe mantenerse inquebrantable en cada etapa.*"
             )

        return None

# Singleton Instance
supervisor = SupervisorPersona()

def get_knowledge_response(query: str):
    # Wrapper for existing calls
    return supervisor.respond(query)
