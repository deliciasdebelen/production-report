#!/bin/bash
# Script para instalar Docker y desplegar la aplicación
# Ejecutar en el servidor: bash install-and-deploy.sh

set -e

echo "========================================="
echo "  INSTALACIÓN DE DOCKER Y DESPLIEGUE"
echo "========================================="
echo ""

# Verificar si Docker ya está instalado
if command -v docker &> /dev/null; then
    echo "✓ Docker ya está instalado"
    docker --version
else
    echo "[1/3] Instalando Docker..."
    
    # Descargar e instalar Docker
    if [ -f "get-docker.sh" ]; then
        echo "Usando script descargado..."
    else
        curl -fsSL https://get.docker.com -o get-docker.sh
    fi
    
    sudo sh get-docker.sh
    
    # Agregar usuario al grupo docker
    sudo usermod -aG docker $USER
    
    echo "✓ Docker instalado exitosamente"
fi

# Verificar Docker Compose
if docker compose version &> /dev/null; then
    echo "✓ Docker Compose está disponible"
else
    echo "ERROR: Docker Compose no está disponible"
    exit 1
fi

echo ""
echo "[2/3] Clonando repositorio..."

# Crear directorio de apps
mkdir -p ~/apps
cd ~/apps

# Clonar o actualizar repositorio
if [ -d "production-report" ]; then
    echo "Repositorio ya existe, actualizando..."
    cd production-report
    git fetch origin
    git checkout production
    git pull origin production
else
    echo "Clonando repositorio..."
    git clone -b production https://github.com/deliciasdebelen/production-report.git
    cd production-report
fi

echo "✓ Repositorio listo"

echo ""
echo "[3/3] Desplegando aplicación..."

# Construir imagen
docker compose build

# Iniciar contenedores
docker compose up -d

# Verificar estado
docker compose ps

echo ""
echo "========================================="
echo "  ✓ DESPLIEGUE COMPLETADO"
echo "========================================="
echo ""
echo "La aplicación está disponible en:"
echo "  http://192.168.1.79:8000"
echo ""
echo "Credenciales por defecto:"
echo "  Usuario: admin"
echo "  Contraseña: admin"
echo ""
echo "Para ver logs:"
echo "  docker compose logs -f"
echo ""
