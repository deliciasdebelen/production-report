# Guía Final de Despliegue

## ✅ Completado

1. **Configuración Docker**: Todos los archivos creados (Dockerfile, docker-compose.yml, etc.)
2. **Repositorio Git**: Código subido a https://github.com/deliciasdebelen/production-report
3. **Personal Access Token**: Generado y configurado (github_pat_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX)
4. **Conexión SSH**: Verificada exitosamente al servidor 192.168.1.79

## ⚠️ Pendiente: Instalar Docker en el Servidor

El servidor **NO tiene Docker instalado**. Necesitas instalarlo antes de desplegar.

### Opción 1: Instalación Automática (Recomendada)

Conéctate al servidor y ejecuta:

```bash
ssh administrador@192.168.1.79
# Password: GRW7czL3*

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Agregar usuario al grupo docker
sudo usermod -aG docker $USER

# Cerrar sesión y volver a entrar para aplicar cambios
exit
```

### Opción 2: Instalación Manual

Sigue las instrucciones detalladas en `DEPLOY.md`, sección "Preparación del Servidor".

## 📋 Próximos Pasos

Una vez que Docker esté instalado en el servidor:

### 1. Verificar Docker

```bash
ssh administrador@192.168.1.79
docker --version
docker compose version
```

### 2. Clonar y Desplegar

```bash
# Crear directorio
mkdir -p ~/apps
cd ~/apps

# Clonar repositorio
git clone https://github.com/deliciasdebelen/production-report.git
cd production-report

# Cuando Git pida credenciales:
# Username: github@deliciasdebelen.com
# Password: github_pat_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Construir y ejecutar
docker compose build
docker compose up -d

# Verificar
docker compose ps
docker compose logs -f
```

### 3. Acceder a la Aplicación

Abre tu navegador y ve a:
```
http://192.168.1.79:8000
```

Credenciales por defecto:
- Usuario: `admin`
- Contraseña: `admin`

## 🔧 Scripts Disponibles

En tu máquina local (Windows), puedes usar:

- **`push-to-github-with-token.bat`**: Push rápido a GitHub con token incluido
- **`deploy-to-server.bat`**: Despliegue automatizado (requiere Docker instalado en servidor)

## 📚 Documentación

- **README.md**: Documentación general del proyecto
- **DEPLOY.md**: Guía detallada de despliegue
- **GITHUB-SETUP.md**: Guía de configuración de GitHub

## 🆘 Soporte

Si tienes problemas:

1. Consulta la sección de Troubleshooting en `DEPLOY.md`
2. Verifica los logs: `docker compose logs -f`
3. Revisa que Docker esté instalado: `docker --version`

## 📝 Resumen de Credenciales

**GitHub:**
- Email: github@deliciasdebelen.com
- Password: C4rm4l2025
- Token: github_pat_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

**Servidor:**
- IP: 192.168.1.79
- Usuario: administrador
- Password: GRW7czL3*

**Aplicación (por defecto):**
- Usuario: admin
- Password: admin (¡cámbiala después del primer login!)
