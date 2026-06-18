@echo off
REM Script final para push a GitHub con token
REM ==========================================

echo.
echo ========================================
echo   PUSH A GITHUB
echo ========================================
echo.

cd /d "%~dp0"

REM Configurar remote
git remote remove origin 2>nul
git remote add origin https://github.com/deliciasdebelen/production-report.git

REM Renombrar rama
git branch -M main

echo.
echo ========================================
echo CREDENCIALES DE GITHUB
echo ========================================
echo.
echo Cuando Git pida credenciales, usa:
echo.
echo   Username: github@deliciasdebelen.com
echo   Password: github_pat_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
echo.
echo IMPORTANTE: El "Password" es el Personal Access Token,
echo             NO la contraseña de la cuenta.
echo.
echo ========================================
echo.
pause

echo Haciendo push...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   EXITO!
    echo ========================================
    echo.
    echo Codigo subido a:
    echo https://github.com/deliciasdebelen/production-report
    echo.
) else (
    echo.
    echo ERROR: El push fallo
    echo.
)

pause
