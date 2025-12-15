# Script de Configuración de GitHub

## Paso 1: Crear Repositorio en GitHub

1. Abre tu navegador y ve a: https://github.com/new
2. Inicia sesión con:
   - **Usuario**: github@deliciasdebelen.com
   - **Contraseña**: Carmal2025

3. Configura el repositorio:
   - **Repository name**: `production-report`
   - **Description**: `Sistema de gestión y reportes de producción`
   - **Visibility**: Public (o Private si prefieres)
   - **NO marques** "Initialize this repository with a README"

4. Haz clic en **"Create repository"**

## Paso 2: Conectar Repositorio Local con GitHub

Una vez creado el repositorio en GitHub, ejecuta los siguientes comandos en tu terminal:

```bash
cd c:\Users\ovargas\Projects\production-report

# Agregar remote de GitHub
git remote add origin https://github.com/deliciasdebelen/production-report.git

# Renombrar rama a main
git branch -M main

# Push inicial
git push -u origin main
```

Cuando Git pida credenciales:
- **Username**: github@deliciasdebelen.com
- **Password**: Carmal2025

## Paso 3: Verificar

Después del push, verifica en GitHub que todos los archivos se hayan subido correctamente:
https://github.com/deliciasdebelen/production-report

## Comandos Útiles de Git

```bash
# Ver estado del repositorio
git status

# Ver historial de commits
git log --oneline

# Ver remotes configurados
git remote -v

# Hacer cambios y push
git add .
git commit -m "Descripción de cambios"
git push
```

## Siguiente Paso: Despliegue en Servidor

Una vez que el código esté en GitHub, puedes proceder con el despliegue en el servidor siguiendo las instrucciones en `DEPLOY.md`.
