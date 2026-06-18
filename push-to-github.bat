@echo off
REM Script mejorado para push a GitHub con autenticación
REM =====================================================

echo.
echo ========================================
echo   PUSH A GITHUB - Production Report
echo ========================================
echo.

cd /d "%~dp0"

REM Verificar que estamos en el directorio correcto
if not exist "app\main.py" (
    echo ERROR: Este script debe ejecutarse desde el directorio raiz del proyecto
    pause
    exit /b 1
)

echo [1/5] Verificando configuracion de Git...
git remote get-url origin >nul 2>&1
if %errorlevel% equ 0 (
    echo Remote 'origin' ya configurado
    git remote -v
) else (
    echo Configurando remote de GitHub...
    git remote add origin https://github.com/deliciasdebelen/production-report.git
)

echo.
echo [2/5] Renombrando rama a main...
git branch -M main

echo.
echo [3/5] Verificando estado de Git...
git status

echo.
echo [4/5] Preparando push a GitHub...
echo.
echo ========================================
echo IMPORTANTE: Autenticacion de GitHub
echo ========================================
echo.
echo GitHub ya no acepta contraseñas para autenticacion HTTPS.
echo Tienes 2 opciones:
echo.
echo OPCION 1 (Recomendada): Usar Personal Access Token
echo   1. Ve a: https://github.com/settings/tokens
echo   2. Click en "Generate new token" (classic)
echo   3. Selecciona scope: "repo" (acceso completo a repositorios)
echo   4. Copia el token generado
echo   5. Usa el token como contraseña cuando Git lo pida
echo.
echo OPCION 2: Usar GitHub CLI
echo   1. Instala GitHub CLI: winget install GitHub.cli
echo   2. Ejecuta: gh auth login
echo   3. Sigue las instrucciones
echo.
echo ========================================
echo.
echo Presiona cualquier tecla para continuar con el push...
echo (Se te pediran credenciales)
pause >nul

echo.
echo [5/5] Haciendo push a GitHub...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   PUSH COMPLETADO EXITOSAMENTE!
    echo ========================================
    echo.
    echo El codigo esta en:
    echo https://github.com/deliciasdebelen/production-report
    echo.
) else (
    echo.
    echo ========================================
    echo   ERROR EN EL PUSH
    echo ========================================
    echo.
    echo Si el error es de autenticacion (403):
    echo   - Necesitas un Personal Access Token
    echo   - Ve a: https://github.com/settings/tokens
    echo   - Genera un token con permisos "repo"
    echo   - Usa el token como contraseña
    echo.
    echo Si el error es que el repositorio no existe:
    echo   - Crea el repositorio en: https://github.com/new
    echo   - Nombre: production-report
    echo   - NO inicialices con README
    echo.
)

echo.
pause
