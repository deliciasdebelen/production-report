# Guía de Despliegue - Production Report

Esta guía detalla el proceso de despliegue de la aplicación en un servidor usando Docker y Git.

## Requisitos del Servidor

### Hardware Mínimo
- CPU: 2 cores
- RAM: 2GB
- Disco: 10GB disponibles

### Software Requerido
- Sistema Operativo: Linux (Ubuntu 20.04+ recomendado) o Windows Server
- Docker 20.10+
- Docker Compose 2.0+
- Git 2.0+
- Acceso SSH

## Preparación del Servidor

### 1. Instalar Docker (Ubuntu/Debian)

```bash
# Actualizar paquetes
sudo apt-get update

# Instalar dependencias
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Agregar clave GPG de Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Agregar repositorio
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Verificar instalación
docker --version
docker compose version
```

### 2. Configurar Usuario Docker

```bash
# Agregar usuario al grupo docker
sudo usermod -aG docker $USER

# Aplicar cambios (o cerrar sesión y volver a entrar)
newgrp docker

# Verificar
docker ps
```

### 3. Instalar Git

```bash
sudo apt-get install -y git
git --version
```

## Despliegue Inicial

### 1. Conectar al Servidor

```bash
ssh administrador@192.168.1.79
```

### 2. Configurar Git

```bash
# Configurar credenciales de Git
git config --global user.name "Delicias de Belen"
git config --global user.email "github@deliciasdebelen.com"

# Configurar credential helper para guardar credenciales
git config --global credential.helper store
```

### 3. Clonar el Repositorio

```bash
# Crear directorio para aplicaciones
mkdir -p ~/apps
cd ~/apps

# Clonar repositorio
git clone https://github.com/deliciasdebelen/production-report.git
cd production-report
```

**Nota**: Al clonar, Git pedirá las credenciales:
- Usuario: `github@deliciasdebelen.com`
- Contraseña: `Carmal2025`

### 4. Configurar Variables de Entorno (Opcional)

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar variables si es necesario
nano .env
```

### 5. Construir y Ejecutar

```bash
# Construir imagen Docker
docker compose build

# Ejecutar en modo detached
docker compose up -d

# Verificar estado
docker compose ps

# Ver logs
docker compose logs -f
```

### 6. Verificar Funcionamiento

```bash
# Verificar que el contenedor está corriendo
docker compose ps

# Verificar logs
docker compose logs web

# Probar endpoint
curl http://localhost:8000/login
```

Desde tu navegador, accede a:
```
http://192.168.1.79:8000
```

## Actualización de la Aplicación

### Método 1: Pull + Rebuild

```bash
# Conectar al servidor
ssh administrador@192.168.1.79

# Ir al directorio del proyecto
cd ~/apps/production-report

# Detener contenedores
docker compose down

# Actualizar código
git pull origin main

# Reconstruir y ejecutar
docker compose build
docker compose up -d

# Verificar
docker compose logs -f
```

### Método 2: Script de Actualización

Crear un script `update.sh`:

```bash
#!/bin/bash
set -e

echo "🔄 Actualizando Production Report..."

# Detener contenedores
echo "⏸️  Deteniendo contenedores..."
docker compose down

# Actualizar código
echo "📥 Descargando última versión..."
git pull origin main

# Reconstruir imagen
echo "🔨 Reconstruyendo imagen..."
docker compose build

# Ejecutar
echo "🚀 Iniciando aplicación..."
docker compose up -d

# Verificar estado
echo "✅ Estado de contenedores:"
docker compose ps

echo "✨ Actualización completada!"
```

Hacer ejecutable y usar:

```bash
chmod +x update.sh
./update.sh
```

## Configuración de Nginx (Opcional)

Si deseas usar un dominio o configurar HTTPS:

### 1. Instalar Nginx

```bash
sudo apt-get install -y nginx
```

### 2. Configurar Reverse Proxy

Crear archivo `/etc/nginx/sites-available/production-report`:

```nginx
server {
    listen 80;
    server_name 192.168.1.79;  # O tu dominio

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Activar configuración:

```bash
sudo ln -s /etc/nginx/sites-available/production-report /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Backup y Restauración

### Backup de Base de Datos

```bash
# Crear directorio de backups
mkdir -p ~/backups

# Backup manual
cp ~/apps/production-report/production.db ~/backups/production-$(date +%Y%m%d-%H%M%S).db

# Backup automático (cron)
# Agregar a crontab (crontab -e):
# 0 2 * * * cp ~/apps/production-report/production.db ~/backups/production-$(date +\%Y\%m\%d).db
```

### Restaurar Backup

```bash
# Detener aplicación
cd ~/apps/production-report
docker compose down

# Restaurar base de datos
cp ~/backups/production-YYYYMMDD.db ./production.db

# Reiniciar aplicación
docker compose up -d
```

## Monitoreo

### Ver Logs en Tiempo Real

```bash
docker compose logs -f web
```

### Ver Estado de Contenedores

```bash
docker compose ps
```

### Ver Uso de Recursos

```bash
docker stats
```

## Troubleshooting

### El contenedor no inicia

```bash
# Ver logs detallados
docker compose logs web

# Verificar configuración
docker compose config

# Reconstruir desde cero
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

### No se puede acceder a la aplicación

```bash
# Verificar que el puerto está abierto
sudo netstat -tlnp | grep 8000

# Verificar firewall (si aplica)
sudo ufw status
sudo ufw allow 8000/tcp
```

### Error de permisos en base de datos

```bash
# Verificar permisos del archivo
ls -la production.db

# Ajustar permisos si es necesario
chmod 664 production.db
```

### Actualización de Git falla

```bash
# Verificar estado
git status

# Descartar cambios locales (¡cuidado!)
git reset --hard origin/main

# Actualizar
git pull
```

## Comandos Útiles

```bash
# Reiniciar aplicación
docker compose restart

# Ver logs de las últimas 100 líneas
docker compose logs --tail=100 web

# Ejecutar comando dentro del contenedor
docker compose exec web bash

# Limpiar imágenes antiguas
docker image prune -a

# Limpiar todo (¡cuidado!)
docker system prune -a --volumes
```

## Seguridad

### Recomendaciones

1. **Cambiar credenciales por defecto**: Cambiar la contraseña del usuario admin
2. **Firewall**: Configurar firewall para permitir solo puertos necesarios
3. **Backups regulares**: Configurar backups automáticos
4. **Actualizaciones**: Mantener Docker y el sistema operativo actualizados
5. **HTTPS**: Configurar certificados SSL si se expone a internet

### Configurar Firewall

```bash
# Habilitar firewall
sudo ufw enable

# Permitir SSH
sudo ufw allow 22/tcp

# Permitir aplicación
sudo ufw allow 8000/tcp

# Verificar estado
sudo ufw status
```

## Contacto

Para soporte técnico, contactar al equipo de desarrollo.
