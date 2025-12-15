@echo off
REM Script de Despliegue Completo para Production Report
REM =====================================================

echo.
echo ========================================
echo   DESPLIEGUE DE PRODUCTION REPORT
echo ========================================
echo.

REM Verificar que estamos en el directorio correcto
if not exist "app\main.py" (
    echo ERROR: Este script debe ejecutarse desde el directorio raiz del proyecto
    pause
    exit /b 1
)

echo [1/4] Configurando Git...
echo.

REM Verificar si ya existe el remote
git remote get-url origin >nul 2>&1
if %errorlevel% equ 0 (
    echo Remote 'origin' ya existe. Saltando configuracion...
) else (
    echo Agregando remote de GitHub...
    git remote add origin https://github.com/deliciasdebelen/production-report.git
    if %errorlevel% neq 0 (
        echo ERROR: No se pudo agregar el remote
        pause
        exit /b 1
    )
)

echo.
echo [2/4] Renombrando rama a main...
git branch -M main
if %errorlevel% neq 0 (
    echo ERROR: No se pudo renombrar la rama
    pause
    exit /b 1
)

echo.
echo [3/4] Haciendo push a GitHub...
echo.
echo NOTA: Se te pediran las credenciales de GitHub:
echo   Usuario: github@deliciasdebelen.com
echo   Password: C4rm4l2025
echo.
pause

git push -u origin main
if %errorlevel% neq 0 (
    echo.
    echo ERROR: No se pudo hacer push a GitHub
    echo.
    echo Posibles causas:
    echo   1. El repositorio no existe en GitHub (crealo en https://github.com/new)
    echo   2. Credenciales incorrectas
    echo   3. No tienes permisos para este repositorio
    echo.
    pause
    exit /b 1
)

echo.
echo [4/4] Verificando...
git remote -v
echo.

echo ========================================
echo   PUSH COMPLETADO EXITOSAMENTE!
echo ========================================
echo.
echo El codigo esta ahora en:
echo https://github.com/deliciasdebelen/production-report
echo.
echo Siguiente paso: Desplegar en el servidor
echo Consulta DEPLOY.md para instrucciones detalladas
echo.
pause
