#!/bin/bash
# pg_backup.sh - Script para respaldar la base de datos PostgreSQL de produccion-report
# Este script está diseñado para ejecutarse vía Cron en el servidor 192.168.1.79

# Configuración
CONTAINER_NAME="production-report-db"
DB_USER="app_user"
DB_NAME="production_db"
BACKUP_DIR="/home/administrador/apps/production-report/backups"
DATE=$(date +"%Y%m%d_%H%M%S")
FILENAME="pg_backup_${DATE}.sql.gz"
RETENTION_DAYS=30

# Crear directorio de respaldos si no existe
mkdir -p "$BACKUP_DIR"

echo "Iniciando respaldo de la base de datos $DB_NAME en el contenedor $CONTAINER_NAME..."

# Ejecutar pg_dump dentro del contenedor y comprimir la salida al instante
docker exec -t "$CONTAINER_NAME" pg_dump -U "$DB_USER" -Fc "$DB_NAME" > "${BACKUP_DIR}/${FILENAME}"

if [ $? -eq 0 ]; then
    echo "✅ Respaldo exitoso: ${BACKUP_DIR}/${FILENAME}"
    
    # Limpiar respaldos antiguos (más antiguos que RETENTION_DAYS)
    echo "Limpiando respaldos más antiguos de $RETENTION_DAYS días..."
    find "$BACKUP_DIR" -name "pg_backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete
    echo "Limpieza completada."
else
    echo "❌ Error al generar el respaldo de la base de datos."
    exit 1
fi
