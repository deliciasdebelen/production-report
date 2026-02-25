
from fpdf import FPDF
import os
from datetime import datetime

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Reporte de Proyecto: Production Report App', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, title, 0, 1, 'L', 1)
        self.ln(4)

    def chapter_body(self, body):
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 5, body)
        self.ln()

    def add_table(self, title, header_data, row_data):
        self.chapter_title(title)
        self.set_font('Arial', 'B', 9)
        # Calculate col widths
        col_w = 45
        for col in header_data:
            self.cell(col_w, 7, col, 1)
        self.ln()
        self.set_font('Arial', '', 9)
        for row in row_data:
            for item in row:
                self.cell(col_w, 7, str(item), 1)
            self.ln()
        self.ln()

pdf = PDF()
pdf.add_page()
pdf.set_auto_page_break(auto=True, margin=15)

# --- 1. Reporte de Ejecución ---
pdf.chapter_title('1. Reporte de Ejecución')
body_exec = """
Se han completado las siguientes tareas en el proyecto 'Production Report':

1. Implementación del Módulo de Logística:
   - Se crearon las tablas en base de datos para Despachos, Recepción de Mercancía y Recepción de Producción.
   - Se implementaron las rutas (routers/logistics.py) y plantillas HTML correspondientes.
   - Se integró el dashboard de logística.

2. Actualización de UI:
   - Se refrescó la interfaz de usuario para formularios globales (Reporte, Planificación).
   - Se unificó el estilo usando un dashboard centralizado.

3. Sincronización con GitHub:
   - Se inicializó/configuró el repositorio remoto.
   - Se subieron los cambios a la rama 'main' incluyendo las migraciones y nuevos módulos.
"""
pdf.chapter_body(body_exec)

# --- 2. Manual de Mantenimiento ---
pdf.chapter_title('2. Manual de Mantenimiento')
body_maint = r"""
Requisitos Previos:
- Python 3.10+
- Git

Instalación y Despliegue:

1. Clonar el repositorio:
   git clone https://github.com/deliciasdebelen/production-report.git
   cd production-report

2. Crear Entorno Virtual:
   python -m venv venv
   .\venv\Scripts\activate  (Windows)
   source venv/bin/activate (Linux/Mac)

3. Instalar Dependencias:
   pip install -r requirements.txt

4. Configuración de Base de Datos:
   - Asegúrese de que SQLite esté disponible (por defecto app.db).
   - Ejecutar migraciones si es necesario:
     python migrate_db.py  (o script personalizado de migración)
     
5. Ejecutar la Aplicación:
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Mantenimiento Común:
- Para agregar campos a la BD: Modificar app/models.py y ejecutar scripts de migración (p.ej. alembic si estuviera configurado, o manualmente).
- Logs: Revisar la salida de la consola de uvicorn para errores.
"""
pdf.chapter_body(body_maint.strip())

# --- 3. Diagrama Entidad-Relación (Descripción) ---
pdf.chapter_title('3. Diagrama Entidad-Relación (Descripción)')
body_er = """
El sistema utiliza una base de datos relacional (SQLite por defecto) con las siguientes relaciones clave:

[ ProductionReport ] 1 --- * [ LogisticsReceptionProduction ]
(Un reporte de producción puede tener múltiples recepciones en logística, vinculado por production_report_id, aunque actualmente es un vínculo lógico por String).

[ LogisticsReceptionMerchandise ] y [ LogisticsDispatch ] operan independientemente, rasteando movimientos externos.

[ User ] maneja la autenticación y roles (1=KPI, 2=Prod, 3=Plan, 4=Admin, 5=Logística).

[ ProductionPlanning ] almacena las órdenes planificadas, vinculadas lógicamente a los reportes por 'order_number'.
"""
pdf.chapter_body(body_er)

# --- 4. Diccionario de Datos ---
pdf.chapter_title('4. Diccionario de Datos')

# Table: ProductionReport
columns_pr = [
    ("id", "String (PK)", "UUID + Date"),
    ("batch_qty", "Integer", "Cantidad de lotes"),
    ("kg_produced", "Float", "Kg producidos"),
    ("status", "String", "Estado (Pending/Confirmed)"),
]
pdf.set_font('Arial', 'B', 10)
pdf.cell(0, 10, 'Tabla: production_reports', 0, 1)
pdf.set_font('Arial', '', 9)
for row in columns_pr:
    pdf.cell(50, 7, row[0], 1)
    pdf.cell(40, 7, row[1], 1)
    pdf.cell(80, 7, row[2], 1)
    pdf.ln()
pdf.ln()

# Table: ProductionPlanning
columns_pp = [
    ("id", "Integer (PK)", "Auto-increment"),
    ("order_number", "String", "Número de orden único"),
    ("date", "String", "Fecha YYYY-MM-DD"),
    ("article", "String", "Artículo a producir"),
]
pdf.set_font('Arial', 'B', 10)
pdf.cell(0, 10, 'Tabla: production_planning', 0, 1)
pdf.set_font('Arial', '', 9)
for row in columns_pp:
    pdf.cell(50, 7, row[0], 1)
    pdf.cell(40, 7, row[1], 1)
    pdf.cell(80, 7, row[2], 1)
    pdf.ln()
pdf.ln()

# Table: LogisticsReceptionProduction
columns_lrp = [
    ("id", "Integer (PK)", "Auto-increment"),
    ("production_report_id", "String", "Link a reporte"),
    ("product_name", "String", "Nombre del producto"),
    ("quantity", "Float", "Cantidad recibida"),
]
pdf.set_font('Arial', 'B', 10)
pdf.cell(0, 10, 'Tabla: logistics_reception_production', 0, 1)
pdf.set_font('Arial', '', 9)
for row in columns_lrp:
    pdf.cell(50, 7, row[0], 1)
    pdf.cell(40, 7, row[1], 1)
    pdf.cell(80, 7, row[2], 1)
    pdf.ln()
pdf.ln()

# Output
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
output_file = os.path.join(desktop_path, "Reporte_Proyecto_ProductionReport.pdf")
pdf.output(output_file, 'F')
print(f"PDF generado exitosamente en: {output_file}")
