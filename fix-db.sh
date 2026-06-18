#!/bin/bash
# Script para corregir permisos y reiniciar la aplicación
set -e

echo "Corrigiendo permisos y reiniciando..."

# Asegurar que el directorio data existe y tiene permisos 777 (para evitar problemas con usuario docker)
mkdir -p data
sudo chmod -R 777 data

# Actualizar código
git pull

# Reconstruir y reiniciar
/usr/local/bin/docker-compose down
/usr/local/bin/docker-compose build
/usr/local/bin/docker-compose up -d

echo "Verificando..."
sleep 5
/usr/local/bin/docker-compose ps
/usr/local/bin/docker-compose logs --tail=20
