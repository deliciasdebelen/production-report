# Documentación Técnica - Sistema de Reporte de Producción

Esta documentación detalla la arquitectura, procesos y flujos, diseño de base de datos (ERD) y los puntos de acceso del sistema en su estado actual de producción.

## 1. Información General y Accesos

- **URL de Acceso (Dashboard/App):** `http://192.168.1.73:8000`
- **Dirección IP del Servidor:** `192.168.1.73`
- **Puerto Explotado:** `8000`
- **Base de Datos:** SQLite (`production.db`)
- **Tecnología Base:** Backend en FastAPI (Python 3.11+), y Frontend usando HTML5/CSS3/Vanilla JS (Plantillas Jinja2) + Despliegue con Docker.

### 1.1 Credenciales y Accesos al Sistema
Las credenciales maestras por defecto en el sistema son:
- **Usuario Admin:** `admin`
- **Contraseña Admin:** `admin`

*(Nota: En producción se recomienda encarecidamente cambiar estos datos y generar usuarios según la jerarquía del rol).*

### 1.2 Jerarquía de Roles de Usuario
- **1** - Visualización (Only KPIs)
- **2** - Producción (Creación de Reportes de Producción)
- **3** - Planificación (Creación de Órdenes de Producción)
- **4** - Admin (Acceso Total + Mantenimiento)
- **5** - Almacén
- **6** - Inventario (Capturas de Stock)
- **7** - Patrimonial
- **8** - Director

---

## 2. Diagrama de Base de Datos y Entidad-Relación (ERD)

A continuación se presente el modelo simplificado de las relaciones principales que rigen la lógica de negocio (Planificación, Producción, Inventario y Logística).

```mermaid
erDiagram
    USERS ||--o{ ROLE : belongs_to
    USERS ||--o{ INVENTORY_CAPTURE : creates
    USERS ||--o{ INVENTORY_CAPTURE_HEADER : creates
    USERS ||--o{ SUPPORT_TICKET : creates
    
    PRODUCTION_PLANNING ||--o{ PRODUCTION_REPORT : satisfies
    
    PRODUCTION_REPORT {
        string id PK
        string order_number "Correlativo de Despacho"
        int batch_qty "Lotes"
        string article_type "Artículo"
        float kg_produced "Kg Producidos"
        float cons_qty "Consumo Rápido"
        string status "Pending / Confirmed"
        text planning_order_ids FK "Referencia a Planificación"
    }
    
    PRODUCTION_PLANNING {
        int id PK
        string order_number
        string date "Fecha"
        string article "Artículo"
        string status "Pending / Processed"
        int units_pending "Count-down Producción"
        float kg "Metaje Esperado"
    }
    
    INVENTORY_CAPTURE {
        int id PK
        string capture_type "Inicio o Cierre"
        string article_code
        float quantity
        string capture_date
        int user_id FK
    }
    
    INVENTORY_CAPTURE_HEADER ||--|{ INVENTORY_CAPTURE_LINE : contains_lines
    INVENTORY_CAPTURE_HEADER {
        int id PK
        string correlative "Lote Auditoría"
        string status
        int user_id FK
    }
    
    INVENTORY_CAPTURE_LINE {
        int id PK
        int header_id FK
        string article_code
        string batch
        float quantity
    }
    
    LOGISTICS_DISPATCH {
        int id PK
        string client_destination
        string document_ref "Referencia (Ej: Factura)"
        text items_json "Detalle Despacho"
        int route_id FK
    }
    
    SUPPORT_TICKET {
        int id PK
        string code "Ej: SOP-2024-001"
        int created_by_id FK
        int department_id FK
        string description
    }
    
    USERS {
        int id PK
        string username
        string password_hash
        int role FK
    }
    
    ROLE {
        int id PK
        string name
        text permissions
    }
```

---

## 3. Diagramas de Flujo y Procesos

### 3.1 Flujo General y Ecosistema de Áreas
Cómo interactúan los diferentes departamentos y la correlación de datos de inicio a fin.

```mermaid
flowchart LR
    Admin[Director / Admin] -->|Autoriza y Evalúa| KPIs[Dashboard Resumen]
    Planificador[Área de Planificación] -->|Carga demanda diaria| PP(Órdenes de Planificación)
    Produccion[Área de Producción] -->|Procesa lotes físicos| PR(Reportes de Producción)
    Logistica[Logística / Almacén] -->|Ejecuta salidas a clientes| LD(Despachos / Recepción)
    Mantenimiento[Soporte / TI] -->|Supervisa estabilidad| ST(Tickets de Soporte)
    AuditoriaIA[Auditoría IA] -->|Verifica pesos e inconsistencias| Mismatch(Alertas de Mismatch)
    
    PR -.->|Satisface & descuenta unidades| PP
    LD -.->|Descuenta Stock de| PR
    LD -.->|Analizado por| AuditoriaIA
```

### 3.2 Diagrama de Proceso de Producción
Un esquema detallado paso a paso de lo que ocurre cuando se inicia el día laboral.

```mermaid
flowchart TD
    A([Inicio de Día Laboral]) --> B([Crear Planificación Producción])
    B --> C{¿Materia Prima Lista?}
    C -- No --> D[Recepción Interna de Bodega / Proveedor]
    C -- Sí --> E[Inicio de Elaboración en Planta]
    D --> E
    
    E --> F[Registro de 'Reporte de Producción' en App]
    F --> G[El Sistema descuenta automáticamente 'units_pending' del Plan de Producción]
    G --> H{¿Queda saldo pendiente \nen la Orden?}
    H -- Sí --> E
    H -- No --> I[Estado de Orden de \nPlanificación pasa a PROCESSED]
    I --> J[Mercancía Terminada Disponible para Almacén]
    J --> K[Logística Dispatch - Despacho Local / a Cliente]
    K --> L[Guardado Logs, Actualización de Inventario y ETL]
    L --> Z([Fin de Ciclo])
```

## 4. Estructura y Componentes Clave

1. **Servicios de Automatización Back-End (Cron / Scheduler):**
   - El sistema tiene `scheduler` de alertas automáticas corriendo en Background para detectar "Mismatch" o inconsistencias (Archivos: `app/services/automation_scheduler.py` y `mismatch_scheduler.py`).

2. **Copias de Seguridad Replicadas (Profit Plus):**
   - Existen modelos tipo ETL que clonan datos transitorios (`ProfitArticulo`, `ProfitStockAlmacen`) de un ERP secundario o antiguo para conciliar Data.

3. **Asistente de Auditoría (IA Integrada):**
   - Existen registros de `AuditLog` y `SystemInsight` donde las métricas recolectan despachos vs unidades producidas. Si la AI detecta merma sospechosa o desviaciones en peso (por ejemplo, empacado vs lo reportado), crea una bandera en tiempo real en la pestaña del Asistente (`/assistant`).

---
**Nota final para Despliegues / Updates:** Cualquier actualización debe ser manejada usando el clúster de Docker apuntando al repositorio central o mediante archivo Compose usando comando estándar `docker compose up -d --build`.
