#!/bin/bash
# Script de Despliegue en Servidor
# ==================================

set -e  # Salir si hay errores

SERVER_USER="administrador"
SERVER_IP="192.168.1.79"
SERVER_PATH="~/apps/production-report"
REPO_URL="https://github.com/deliciasdebelen/production-report.git"

echo ""
echo "========================================"
echo "  DESPLIEGUE EN SERVIDOR"
echo "========================================"
echo ""
echo "Servidor: $SERVER_USER@$SERVER_IP"
echo "Ruta: $SERVER_PATH"
echo ""

# Función para ejecutar comandos en el servidor
run_remote() {
    ssh "$SERVER_USER@$SERVER_IP" "$1"
}

echo "[1/6] Conectando al servidor..."
ssh -q "$SERVER_USER@$SERVER_IP" exit
if [ $? -ne 0 ]; then
    echo "ERROR: No se pudo conectar al servidor"
    echo "Verifica:"
    echo "  1. La IP del servidor es correcta"
    echo "  2. El usuario 'administrador' existe"
    echo "  3. Tienes acceso SSH"
    exit 1
fi
echo "✓ Conexión exitosa"

echo ""
echo "[2/6] Verificando Docker en el servidor..."
run_remote "docker --version && docker compose version" || {
    echo "ERROR: Docker no está instalado en el servidor"
    echo "Instala Docker siguiendo las instrucciones en DEPLOY.md"
    exit 1
}
echo "✓ Docker está instalado"

echo ""
echo "[3/6] Creando directorio de aplicaciones..."
run_remote "mkdir -p ~/apps"
echo "✓ Directorio creado"

echo ""
echo "[4/6] Clonando repositorio..."
run_remote "cd ~/apps && if [ -d production-report ]; then cd production-report && git pull; else git clone $REPO_URL; fi"
echo "✓ Código descargado"

echo ""
echo "[5/6] Construyendo imagen Docker..."
run_remote "cd $SERVER_PATH && docker compose build"
echo "✓ Imagen construida"

echo ""
echo "[6/6] Iniciando aplicación..."
run_remote "cd $SERVER_PATH && docker compose up -d"
echo "✓ Aplicación iniciada"

echo ""
echo "========================================"
echo "  DESPLIEGUE COMPLETADO!"
echo "========================================"
echo ""
echo "La aplicación está disponible en:"
echo "  http://$SERVER_IP:8000"
echo ""
echo "Para ver logs:"
echo "  ssh $SERVER_USER@$SERVER_IP"
echo "  cd $SERVER_PATH"
echo "  docker compose logs -f"
echo ""
