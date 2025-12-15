@echo off
REM Script de Despliegue en Servidor (Windows)
REM ===========================================

setlocal enabledelayedexpansion

set SERVER_USER=administrador
set SERVER_IP=192.168.1.79
set SERVER_PATH=~/apps/production-report
set REPO_URL=https://github.com/deliciasdebelen/production-report.git

echo.
echo ========================================
echo   DESPLIEGUE EN SERVIDOR
echo ========================================
echo.
echo Servidor: %SERVER_USER%@%SERVER_IP%
echo Ruta: %SERVER_PATH%
echo.
echo NOTA: Este script requiere que tengas SSH configurado
echo       y acceso al servidor.
echo.
echo Credenciales del servidor:
echo   Usuario: %SERVER_USER%
echo   Password: GRW7czL3*
echo.
pause

echo.
echo [1/6] Verificando conexion SSH...
ssh -o ConnectTimeout=5 %SERVER_USER%@%SERVER_IP% exit
if %errorlevel% neq 0 (
    echo ERROR: No se pudo conectar al servidor
    echo.
    echo Verifica:
    echo   1. La IP del servidor es correcta: %SERVER_IP%
    echo   2. El usuario existe: %SERVER_USER%
    echo   3. Tienes acceso SSH
    echo   4. OpenSSH esta instalado en Windows
    echo.
    pause
    exit /b 1
)
echo OK - Conexion exitosa
echo.

echo [2/6] Verificando Docker en el servidor...
ssh %SERVER_USER%@%SERVER_IP% "docker --version && docker compose version"
if %errorlevel% neq 0 (
    echo ERROR: Docker no esta instalado en el servidor
    echo Instala Docker siguiendo las instrucciones en DEPLOY.md
    pause
    exit /b 1
)
echo OK - Docker esta instalado
echo.

echo [3/6] Creando directorio de aplicaciones...
ssh %SERVER_USER%@%SERVER_IP% "mkdir -p ~/apps"
echo OK - Directorio creado
echo.

echo [4/6] Clonando/Actualizando repositorio...
echo.
echo NOTA: Se pediran las credenciales de GitHub en el servidor:
echo   Usuario: github@deliciasdebelen.com
echo   Password: C4rm4l2025
echo.
ssh %SERVER_USER%@%SERVER_IP% "cd ~/apps && if [ -d production-report ]; then cd production-report && git pull; else git clone %REPO_URL%; fi"
if %errorlevel% neq 0 (
    echo ERROR: No se pudo clonar el repositorio
    echo Verifica que el repositorio existe en GitHub
    pause
    exit /b 1
)
echo OK - Codigo descargado
echo.

echo [5/6] Construyendo imagen Docker...
ssh %SERVER_USER%@%SERVER_IP% "cd %SERVER_PATH% && docker compose build"
if %errorlevel% neq 0 (
    echo ERROR: No se pudo construir la imagen Docker
    pause
    exit /b 1
)
echo OK - Imagen construida
echo.

echo [6/6] Iniciando aplicacion...
ssh %SERVER_USER%@%SERVER_IP% "cd %SERVER_PATH% && docker compose up -d"
if %errorlevel% neq 0 (
    echo ERROR: No se pudo iniciar la aplicacion
    pause
    exit /b 1
)
echo OK - Aplicacion iniciada
echo.

echo ========================================
echo   DESPLIEGUE COMPLETADO!
echo ========================================
echo.
echo La aplicacion esta disponible en:
echo   http://%SERVER_IP%:8000
echo.
echo Para ver logs:
echo   ssh %SERVER_USER%@%SERVER_IP%
echo   cd %SERVER_PATH%
echo   docker compose logs -f
echo.
echo Credenciales por defecto:
echo   Usuario: admin
echo   Password: admin
echo.
pause
