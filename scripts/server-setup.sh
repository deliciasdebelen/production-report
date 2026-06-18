#!/bin/bash
set -e

echo "=== Preparando directorio del proyecto ==="
mkdir -p ~/production-report
cd ~/production-report

if [ -f ~/production-report.tar.gz ]; then
    echo "Extrayendo proyecto..."
    tar -xzf ~/production-report.tar.gz -C ~/production-report/
    rm ~/production-report.tar.gz
    echo "Archivos principales:"
    ls | head -20
fi

echo "=== Configurando .env ==="
if [ ! -f ~/production-report/.env ]; then
    SECRET=$(openssl rand -hex 32)
    printf "DATABASE_URL=postgresql://app_user:production_password@db:5432/production_db\nSECRET_KEY=%s\nHOST=0.0.0.0\nPORT=8000\nPYTHONUNBUFFERED=1\nOPENSSL_CONF=/etc/ssl/openssl.cnf\n" "$SECRET" > ~/production-report/.env
    echo ".env creado con SECRET_KEY segura"
else
    echo ".env ya existe (preservado)"
fi

echo "=== Verificando .env ==="
grep -v SECRET_KEY ~/production-report/.env

echo "=== Levantando Docker Compose ==="
cd ~/production-report
docker compose down --remove-orphans 2>/dev/null || true
docker compose up -d --build
echo "Esperando 20 segundos para que los servicios arranquen..."
sleep 20

echo "=== Estado de contenedores ==="
docker compose ps

echo "=== Verificando app en puerto 8000 ==="
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8000/login 2>/dev/null || echo "App todavia iniciando..."

echo "=== SETUP COMPLETADO ==="
