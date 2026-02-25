# Reporte de Producción

Sistema de gestión y reportes de producción desarrollado con FastAPI.

## Características

- 📊 **Dashboard de KPIs**: Visualización de métricas clave de producción
- 📝 **Reportes de Producción**: Registro detallado de producción diaria
- 📅 **Planificación**: Sistema de planificación de producción
- 🚚 **Traslados**: Gestión de traslados entre ubicaciones
- 👥 **Gestión de Usuarios**: Sistema de autenticación con roles
- 🔧 **Mantenimiento**: Panel de administración para gestión de datos

## Tecnologías

- **Backend**: FastAPI + SQLAlchemy
- **Frontend**: HTML5 + CSS3 + JavaScript (Vanilla)
- **Base de Datos**: SQLite
- **Autenticación**: Cookie-based sessions con bcrypt

## Instalación Local

### Requisitos Previos

- Python 3.11+
- pip

### Pasos

1. Clonar el repositorio:
```bash
git clone https://github.com/deliciasdebelen/production-report.git
cd production-report
```

2. Crear entorno virtual:
```bash
python -m venv venv
```

3. Activar entorno virtual:
```bash
# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

4. Instalar dependencias:
```bash
pip install -r requirements.txt
```

5. Ejecutar la aplicación:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

6. Acceder a la aplicación:
```
http://localhost:8000
```

**Credenciales por defecto:**
- Usuario: `admin`
- Contraseña: `admin`

## Despliegue con Docker

### Requisitos Previos

- Docker
- Docker Compose

### Pasos

1. Clonar el repositorio:
```bash
git clone https://github.com/deliciasdebelen/production-report.git
cd production-report
```

2. Construir y ejecutar:
```bash
docker-compose up -d
```

3. Verificar estado:
```bash
docker-compose ps
```

4. Ver logs:
```bash
docker-compose logs -f
```

5. Detener:
```bash
docker-compose down
```

## Estructura del Proyecto

```
production-report/
├── app/
│   ├── main.py              # Aplicación principal FastAPI
│   ├── models.py            # Modelos SQLAlchemy
│   ├── schemas.py           # Schemas Pydantic
│   ├── database.py          # Configuración de base de datos
│   ├── auth_utils.py        # Utilidades de autenticación
│   ├── dependencies.py      # Dependencias de FastAPI
│   ├── routers/             # Routers modulares
│   │   ├── external.py      # Endpoints externos
│   │   └── traslados.py     # Gestión de traslados
│   ├── templates/           # Templates HTML
│   └── static/              # Archivos estáticos
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Roles de Usuario

- **Admin (4)**: Acceso completo al sistema
- **Planificación (3)**: Acceso a planificación y dashboard
- **Producción (2)**: Acceso a reportes de producción y dashboard
- **Visualización (1)**: Solo acceso a dashboard

## Comandos Útiles

### Docker

```bash
# Reconstruir imagen
docker-compose build

# Ejecutar en modo detached
docker-compose up -d

# Ver logs en tiempo real
docker-compose logs -f web

# Reiniciar servicio
docker-compose restart web

# Acceder al contenedor
docker-compose exec web bash

# Limpiar todo
docker-compose down -v
```

### Base de Datos

```bash
# Backup de base de datos
cp production.db production.db.backup

# Restaurar backup
cp production.db.backup production.db
```

## Desarrollo

Para contribuir al proyecto:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## Licencia

Uso interno - Delicias de Belén

## Soporte

Para soporte, contactar al equipo de desarrollo.
